<script lang="ts">
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';

  // Props
  let {
    apiUrl = '/api/v2/aggregates/minister-network/',
    width = 1200,
    height = 800,
    limit = 30,
    minValue = 10000,
    minMeetings = 5,
    currentOnly = true
  }: {
    apiUrl?: string;
    width?: number;
    height?: number;
    limit?: number;
    minValue?: number;
    minMeetings?: number;
    currentOnly?: boolean;
  } = $props();

  // State
  let container: HTMLDivElement;
  let svg: SVGSVGElement;
  let nodes: any[] = $state([]);
  let links: any[] = $state([]);
  let processedLinks: any[] = $state([]);
  let stats: any = $state({});
  let loading = $state(true);
  let error = $state<string | null>(null);
  let hoveredNode: any = $state(null);
  let pinnedNode: any = $state(null);
  let simulation: any;
  let simulationReady = $state(false);

  // Physics Settings (State)
  let chargeStrength = $state(-40);
  let ministerCharge = $state(-590);
  let linkDistance = $state(190);
  let roleLinkDistance = $state(150);
  let gravityX = $state(0.14);
  let gravityY = $state(0.25);
  let collisionPadding = $state(6);
  let showSettings = $state(false);
  let highlightBridges = $state(true);

  // Compute bridge nodes: donors/orgs that connect to 2+ ministers
  const bridgeNodeIds = $derived.by(() => {
    if (nodes.length === 0 || processedLinks.length === 0) return new Set<number>();

    // Build map: node -> set of ministers it connects to
    const nodeToMinisters = new Map<number, Set<number>>();
    const ministerIds = new Set(nodes.filter(n => n.type === 'minister').map(n => n.id));

    processedLinks.forEach(link => {
      if (link.link_type === 'donation' || link.link_type === 'meeting') {
        const src = link.source;
        const tgt = link.target;
        if (src && tgt) {
          if (ministerIds.has(tgt.id) && !ministerIds.has(src.id)) {
            if (!nodeToMinisters.has(src.id)) nodeToMinisters.set(src.id, new Set());
            nodeToMinisters.get(src.id)!.add(tgt.id);
          }
          if (ministerIds.has(src.id) && !ministerIds.has(tgt.id)) {
            if (!nodeToMinisters.has(tgt.id)) nodeToMinisters.set(tgt.id, new Set());
            nodeToMinisters.get(tgt.id)!.add(src.id);
          }
        }
      }
    });

    // Find nodes connecting 2+ ministers
    const bridges = new Set<number>();
    nodeToMinisters.forEach((ministers, nodeId) => {
      if (ministers.size >= 2) {
        bridges.add(nodeId);
      }
    });

    return bridges;
  });

  // Compute corporate bridge nodes: directors/PSCs that connect to 2+ companies
  const corporateBridgeIds = $derived.by(() => {
    if (nodes.length === 0 || processedLinks.length === 0) return new Set<number>();

    // Build map: director/PSC -> set of organizations they connect to
    const personToOrgs = new Map<number, Set<number>>();
    const directorPscIds = new Set(nodes.filter(n => n.type === 'director' || n.type === 'psc').map(n => n.id));
    const orgIds = new Set(nodes.filter(n => n.type === 'organization').map(n => n.id));

    processedLinks.forEach(link => {
      if (link.link_type === 'role') {
        const src = link.source;
        const tgt = link.target;
        if (src && tgt) {
          // Director/PSC -> Organization links
          if (directorPscIds.has(src.id) && orgIds.has(tgt.id)) {
            if (!personToOrgs.has(src.id)) personToOrgs.set(src.id, new Set());
            personToOrgs.get(src.id)!.add(tgt.id);
          }
          if (directorPscIds.has(tgt.id) && orgIds.has(src.id)) {
            if (!personToOrgs.has(tgt.id)) personToOrgs.set(tgt.id, new Set());
            personToOrgs.get(tgt.id)!.add(src.id);
          }
        }
      }
    });

    // Find directors/PSCs connecting 2+ organizations
    const bridges = new Set<number>();
    personToOrgs.forEach((orgs, personId) => {
      if (orgs.size >= 2) {
        bridges.add(personId);
      }
    });

    return bridges;
  });

  function updatePhysics() {
    if (!simulation) return;

    simulation.force('link').distance((d: any) => d.link_type === 'role' ? roleLinkDistance : linkDistance);
    simulation.force('charge').strength((d: any) => d.type === 'minister' ? ministerCharge : chargeStrength);
    simulation.force('x').strength(gravityX);
    simulation.force('y').strength(gravityY);
    simulation.force('collide').radius((d: any) => {
      const r = (d.type === 'director' || d.type === 'psc')
        ? 5 + (d.role_degree || 0) * 6
        : radiusScale(d.total_value);
      return r + collisionPadding;
    });

    simulation.alpha(0.3).restart();
  }

  // Active node is pinned if exists, otherwise hovered
  const activeNode = $derived(pinnedNode || hoveredNode);

  // Compute connected node IDs for the active node (including 2-hop connections)
  const connectedNodeIds = $derived.by(() => {
    if (!activeNode || processedLinks.length === 0) return new Set<number>();

    const connected = new Set<number>();
    connected.add(activeNode.id); // Include the active node itself

    // First pass: direct connections
    const directConnections = new Set<number>();
    processedLinks.forEach(link => {
      if (link.source?.id === activeNode.id) {
        directConnections.add(link.target.id);
        connected.add(link.target.id);
      } else if (link.target?.id === activeNode.id) {
        directConnections.add(link.source.id);
        connected.add(link.source.id);
      }
    });

    // Second pass: 2-hop connections through organizations
    // If hovering minister -> show directors/PSCs of donor orgs
    // If hovering director/PSC -> show ministers their org donated to
    // If hovering org -> show both ministers and directors/PSCs
    const orgIds = new Set(nodes.filter(n => n.type === 'organization').map(n => n.id));
    const ministerIds = new Set(nodes.filter(n => n.type === 'minister').map(n => n.id));

    directConnections.forEach(connectedId => {
      // If the direct connection is an organization, find its directors/PSCs and ministers
      if (orgIds.has(connectedId)) {
        processedLinks.forEach(link => {
          // Role links connect directors/PSCs to organizations
          if (link.link_type === 'role') {
            if (link.source?.id === connectedId) connected.add(link.target.id);
            if (link.target?.id === connectedId) connected.add(link.source.id);
          }
          // Donation links connect organizations to ministers
          if (link.link_type === 'donation') {
            if (link.source?.id === connectedId) connected.add(link.target.id);
            if (link.target?.id === connectedId) connected.add(link.source.id);
          }
        });
      }
      // If the direct connection is a minister, find orgs that donated and their directors
      if (ministerIds.has(connectedId)) {
        processedLinks.forEach(link => {
          if (link.link_type === 'donation') {
            let orgId: number | null = null;
            if (link.target?.id === connectedId && orgIds.has(link.source?.id)) {
              orgId = link.source.id;
            }
            if (orgId) {
              connected.add(orgId);
              // Now find directors/PSCs of this org
              processedLinks.forEach(roleLink => {
                if (roleLink.link_type === 'role') {
                  if (roleLink.source?.id === orgId) connected.add(roleLink.target.id);
                  if (roleLink.target?.id === orgId) connected.add(roleLink.source.id);
                }
              });
            }
          }
        });
      }
    });

    return connected;
  });

  // Scale for node radius based on value - smaller for denser packing
  const radiusScale = $derived(
    d3.scaleSqrt()
      .domain([0, Math.max(...nodes.map(n => n.total_value), 1)])
      .range([4, 32]) // Increased max size slightly
  );

  // Separate scale for donors so they aren't dwarfed by ministers
  const donorScale = $derived(
    d3.scaleSqrt()
      .domain([0, Math.max(...nodes.filter(n => n.type !== 'minister').map(n => n.total_value), 1)])
      .range([4, 24])
  );

  // ... (inside updatePhysics and template)
  
  // Use donorScale for non-ministers
  // ...

  // Natural history color palette — aligned with design system
  const colorMap: Record<string, string> = {
    minister: '#B85450',    // Warm red (design system minister node)
    person: '#5B7355',      // Botanical green
    organization: '#6B5B4F', // Warm brown
    donor: '#5B7355',       // Botanical green
    director: '#4A7BA7',    // Steel blue (design system director)
    psc: '#B87333'          // Copper (design system PSC)
  };

  // Detail panel position: left or right based on active node position
  const detailOnLeft = $derived(activeNode ? activeNode.x > width * 0.55 : false);

  // Compute annotation data for leader lines
  const topBridge = $derived.by(() => {
    if (nodes.length === 0) return null;
    let best: any = null;
    let bestCount = 0;
    nodes.forEach(n => {
      if (bridgeNodeIds.has(n.id) && n.ministerCount > bestCount) {
        best = n;
        bestCount = n.ministerCount;
      }
    });
    return best;
  });

  const largestDonor = $derived.by(() => {
    if (nodes.length === 0) return null;
    let best: any = null;
    let bestVal = 0;
    nodes.forEach(n => {
      if (n.type !== 'minister' && n.total_value > bestVal) {
        best = n;
        bestVal = n.total_value;
      }
    });
    return best;
  });

  async function fetchData() {
    loading = true;
    error = null;

    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        min_value: minValue.toString(),
        min_meetings: minMeetings.toString(),
        current_only: currentOnly.toString()
      });

      const response = await fetch(`${apiUrl}?${params}`);
      if (!response.ok) throw new Error('Failed to fetch network data');

      const data = await response.json();

      // Filter out meetings from the graph (keep donations and roles)
      data.links = data.links.filter((l: any) => l.link_type === 'donation' || l.link_type === 'role');

      // Filter out nodes that are only meeting attendees (no donations and not a minister)
      // Keep ministers, donors (value > 0), directors, and pscs
      data.nodes = data.nodes.filter((n: any) => 
        n.type === 'minister' || 
        n.total_value > 0 || 
        n.type === 'director' || 
        n.type === 'psc'
      );

      // Calculate role degree (connections) for directors/PSCs
      const roleCounts: Record<string, number> = {};
      data.links.forEach((l: any) => {
        if (l.link_type === 'role') {
          // Source is the person ID
          roleCounts[l.source] = (roleCounts[l.source] || 0) + 1;
        }
      });

      data.nodes.forEach((n: any) => {
        if (n.type === 'director' || n.type === 'psc') {
          n.role_degree = roleCounts[n.id] || 0;
        }
      });

      // Identify bridge nodes (connect to multiple ministers)
      const ministerIds = new Set(data.nodes.filter((n: any) => n.type === 'minister').map((n: any) => n.id));
      const nodeMinisterConnections: Record<number, Set<number>> = {};
      data.links.forEach((l: any) => {
        if (l.link_type === 'donation' || l.link_type === 'meeting') {
          const src = l.source;
          const tgt = l.target;
          if (ministerIds.has(tgt)) {
            if (!nodeMinisterConnections[src]) nodeMinisterConnections[src] = new Set();
            nodeMinisterConnections[src].add(tgt);
          }
        }
      });

      // Mark bridge nodes with ministerKey for clustering
      data.nodes.forEach((n: any) => {
        const ministers = nodeMinisterConnections[n.id] || new Set();
        n.ministerCount = ministers.size;
        n.isBridge = n.ministerCount >= 2;
        // Create a key from sorted minister IDs for grouping
        n.ministerKey = Array.from(ministers).sort((a, b) => a - b).join('-');
      });

      // Initialize positions before setting state
      // Group by type first for proper circular distribution
      const ministers = data.nodes.filter((n: any) => n.type === 'minister');
      const directors = data.nodes.filter((n: any) => n.type === 'director' || n.type === 'psc');
      const others = data.nodes.filter((n: any) => n.type !== 'minister' && n.type !== 'director' && n.type !== 'psc');

      const nodesWithPositions = data.nodes.map((node: any) => {
        if (node.type === 'minister') {
          const idx = ministers.indexOf(node);
          const angle = (idx / ministers.length) * 2 * Math.PI;
          return {
            ...node,
            x: width / 2 + Math.cos(angle) * 200,
            y: height / 2 + Math.sin(angle) * 200
          };
        } else if (node.type === 'director' || node.type === 'psc') {
          const idx = directors.indexOf(node);
          const angle = (idx / directors.length) * 2 * Math.PI;
          return {
            ...node,
            x: width / 2 + Math.cos(angle) * 300,
            y: height / 2 + Math.sin(angle) * 300
          };
        } else {
          const idx = others.indexOf(node);
          const angle = (idx / others.length) * 2 * Math.PI;
          return {
            ...node,
            x: width / 2 + Math.cos(angle) * 450,
            y: height / 2 + Math.sin(angle) * 450
          };
        }
      });

      nodes = nodesWithPositions;
      links = data.links;
      stats = data.stats;

      // Set loading to false first so SVG renders
      loading = false;

      // Then initialize simulation on next frame
      requestAnimationFrame(() => {
        initializeSimulation();
      });
    } catch (e) {
      error = e instanceof Error ? e.message : 'Unknown error';
      loading = false;
    }
  }

  function initializeSimulation() {
    if (nodes.length === 0) return;

    // Create node index for links
    const nodeById = new Map(nodes.map(n => [n.id, n]));

    // Convert link source/target to node references
    processedLinks = links.map(l => ({
      ...l,
      source: nodeById.get(l.source),
      target: nodeById.get(l.target)
    })).filter(l => l.source && l.target);

    // Create force simulation - allow overflow past edges
    const padding = -50; // Negative padding allows overflow

    if (simulation) simulation.stop();

    simulation = forceSimulation(nodes)
      .alphaDecay(0.02) // Faster decay so it settles
      .force('link', forceLink(processedLinks)
        .id((d: any) => d.id)
        .distance((d: any) => d.link_type === 'role' ? roleLinkDistance : linkDistance)
        .strength(0.3))
      .force('charge', forceManyBody()
        .strength((d: any) => d.type === 'minister' ? ministerCharge : chargeStrength))
      // Use only forceX/Y for centering (not forceCenter which shifts center of mass)
      .force('x', d3.forceX(width / 2).strength(gravityX))
      .force('y', d3.forceY(height / 2).strength(gravityY))
      .force('collide', forceCollide()
        .radius((d: any) => {
          const r = (d.type === 'director' || d.type === 'psc')
            ? 5 + (d.role_degree || 0) * 6
            : radiusScale(d.total_value);
          return r + collisionPadding; // Add buffer
        }))
      .on('tick', () => {
        // No manual boundary handling - let D3 forces handle it
        // The forceX/Y will keep nodes centered

        // Trigger Svelte reactivity by creating new array references
        nodes = [...nodes];
        processedLinks = [...processedLinks];
      });

    simulationReady = true;
  }

  function handleNodeHover(node: any) {
    if (!pinnedNode) {
      hoveredNode = node;
    }
  }

  function handleNodeLeave() {
    hoveredNode = null;
  }

  function handleNodeClick(node: any) {
    // Toggle pin on click
    pinnedNode = pinnedNode?.id === node.id ? null : node;
  }

  function handleCloseDetail() {
    pinnedNode = null;
    hoveredNode = null;
  }

  function formatCurrency(value: number) {
    if (value >= 1_000_000) return `£${(value / 1_000_000).toFixed(1)}m`;
    if (value >= 1_000) return `£${(value / 1_000).toFixed(0)}k`;
    return `£${value.toFixed(0)}`;
  }

  onMount(() => {
    fetchData();

    return () => {
      if (simulation) simulation.stop();
    };
  });
</script>

<div class="minister-network" bind:this={container}>
  {#if loading}
    <div class="loading">
      <!-- Taxonomic skeleton: faint dot-cloud suggesting graph shape -->
      <svg viewBox="0 0 800 400" class="w-full max-w-[800px] opacity-25" style="min-height: 300px;">
        <defs>
          <pattern id="skel-stipple" width="6" height="6" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="0.5" fill="#6b6b6b" opacity="0.3"/>
            <circle cx="5" cy="5" r="0.4" fill="#6b6b6b" opacity="0.2"/>
          </pattern>
        </defs>
        <!-- Central cluster -->
        <circle cx="400" cy="200" r="45" fill="url(#skel-stipple)"/>
        <circle cx="340" cy="170" r="25" fill="url(#skel-stipple)"/>
        <circle cx="460" cy="230" r="30" fill="url(#skel-stipple)"/>
        <circle cx="350" cy="250" r="20" fill="url(#skel-stipple)"/>
        <circle cx="450" cy="160" r="22" fill="url(#skel-stipple)"/>
        <!-- Outer nodes -->
        <circle cx="240" cy="140" r="14" fill="url(#skel-stipple)"/>
        <circle cx="560" cy="260" r="16" fill="url(#skel-stipple)"/>
        <circle cx="280" cy="300" r="12" fill="url(#skel-stipple)"/>
        <circle cx="520" cy="120" r="13" fill="url(#skel-stipple)"/>
        <circle cx="180" cy="220" r="10" fill="url(#skel-stipple)"/>
        <circle cx="620" cy="180" r="11" fill="url(#skel-stipple)"/>
        <!-- Leader lines to empty labels -->
        <line x1="240" y1="140" x2="170" y2="110" stroke="#6b6b6b" stroke-width="0.5" opacity="0.3"/>
        <rect x="110" y="105" width="58" height="8" fill="#6b6b6b" opacity="0.08" rx="1"/>
        <line x1="560" y1="260" x2="630" y2="290" stroke="#6b6b6b" stroke-width="0.5" opacity="0.3"/>
        <rect x="632" y="285" width="50" height="8" fill="#6b6b6b" opacity="0.08" rx="1"/>
        <line x1="520" y1="120" x2="580" y2="90" stroke="#6b6b6b" stroke-width="0.5" opacity="0.3"/>
        <rect x="582" y="85" width="45" height="8" fill="#6b6b6b" opacity="0.08" rx="1"/>
        <!-- Faint connection lines -->
        <line x1="340" y1="170" x2="400" y2="200" stroke="#6b6b6b" stroke-width="0.5" opacity="0.15"/>
        <line x1="400" y1="200" x2="460" y2="230" stroke="#6b6b6b" stroke-width="0.5" opacity="0.15"/>
        <line x1="350" y1="250" x2="400" y2="200" stroke="#6b6b6b" stroke-width="0.5" opacity="0.15"/>
        <line x1="240" y1="140" x2="340" y2="170" stroke="#6b6b6b" stroke-width="0.5" opacity="0.1"/>
        <line x1="460" y1="230" x2="560" y2="260" stroke="#6b6b6b" stroke-width="0.5" opacity="0.1"/>
      </svg>
      <p class="text-ink-muted text-caption uppercase tracking-wider mt-4">Cataloguing connections...</p>
    </div>
  {:else if error}
    <div class="error">
      <p class="text-economist-red">{error}</p>
    </div>
  {:else}
    <!-- SVG Visualization -->
    <svg
      bind:this={svg}
      viewBox="-100 -50 {width + 200} {height + 100}"
      class="network-svg"
      style="min-height: 600px;"
    >
      <!-- Stipple pattern defs for node halos -->
      <defs>
        <pattern id="stipple-minister" width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.7" fill="#B85450" opacity="0.35"/>
          <circle cx="3" cy="3" r="0.6" fill="#B85450" opacity="0.25"/>
        </pattern>
        <pattern id="stipple-donor" width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.7" fill="#5B7355" opacity="0.35"/>
          <circle cx="3" cy="3" r="0.6" fill="#5B7355" opacity="0.25"/>
        </pattern>
        <pattern id="stipple-person" width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.7" fill="#5B7355" opacity="0.35"/>
          <circle cx="3" cy="3" r="0.6" fill="#5B7355" opacity="0.25"/>
        </pattern>
        <pattern id="stipple-director" width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.7" fill="#4A7BA7" opacity="0.35"/>
          <circle cx="3" cy="3" r="0.6" fill="#4A7BA7" opacity="0.25"/>
        </pattern>
        <pattern id="stipple-psc" width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.7" fill="#B87333" opacity="0.35"/>
          <circle cx="3" cy="3" r="0.6" fill="#B87333" opacity="0.25"/>
        </pattern>
        <pattern id="stipple-organization" width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.7" fill="#6B5B4F" opacity="0.35"/>
          <circle cx="3" cy="3" r="0.6" fill="#6B5B4F" opacity="0.25"/>
        </pattern>
      </defs>

      <!-- Bridge node highlight rings (nodes connecting 2+ ministers) -->
      {#if highlightBridges}
        <g class="bridge-rings">
          {#each nodes.filter(n => bridgeNodeIds.has(n.id)) as node}
            {@const r = (node.type === 'director' || node.type === 'psc')
              ? 5 + (node.role_degree || 0) * 6
              : radiusScale(node.total_value)}
            <circle
              cx={node.x}
              cy={node.y}
              r={r + 6}
              fill="none"
              stroke="rgba(218, 165, 32, 0.8)"
              stroke-width="3"
              class="bridge-ring"
            />
          {/each}
        </g>
      {/if}

      <!-- Corporate bridge rings (directors/PSCs connecting 2+ companies) -->
      {#if highlightBridges}
        <g class="corporate-bridge-rings">
          {#each nodes.filter(n => corporateBridgeIds.has(n.id)) as node}
            {@const r = 5 + (node.role_degree || 0) * 6}
            <circle
              cx={node.x}
              cy={node.y}
              r={r + 6}
              fill="none"
              stroke="rgba(91, 127, 149, 0.8)"
              stroke-width="3"
              class="corporate-bridge-ring"
            />
          {/each}
        </g>
      {/if}

      <!-- Links -->
      <g class="links">
        {#each processedLinks as link}
          {#if link.source?.x && link.target?.x}
            {@const isDonation = link.link_type === 'donation'}
            {@const isRole = link.link_type === 'role'}
            <line
              x1={link.source.x}
              y1={link.source.y}
              x2={link.target.x}
              y2={link.target.y}
              stroke={isDonation ? '#6B5B4F' : (isRole ? '#5B7F95' : '#7B9E87')}
              stroke-opacity={activeNode ?
                (activeNode.id === link.source.id || activeNode.id === link.target.id ? 0.7 : 0.03)
                : 0.15}
              stroke-width={isDonation
                ? Math.max(0.5, Math.log10(link.value / 1000) * 0.8)
                : (isRole ? 1 : Math.max(0.5, Math.log10(link.count + 1) * 1.2))}
              stroke-dasharray={isDonation ? 'none' : (isRole ? '2,2' : '4,2')}
            />
          {/if}
        {/each}
      </g>

      <!-- Nodes -->
      <g class="nodes">
        {#each nodes as node}
          {#if node.x && node.y}
            {@const isActive = activeNode?.id === node.id}
            {@const isPinned = pinnedNode?.id === node.id}
            {@const isConnector = (node.type === 'director' || node.type === 'psc') && node.role_degree > 1}
            {@const baseRadius = (node.type === 'director' || node.type === 'psc')
              ? 5 + (node.role_degree || 0) * 6
              : radiusScale(node.total_value)}
            {@const displayRadius = isActive ? baseRadius * 1.15 : baseRadius}
            {@const isConnected = connectedNodeIds.has(node.id)}
            <g
              class="node"
              class:active={isActive}
              class:pinned={isPinned}
              class:connected={isConnected && !isActive}
              transform="translate({node.x}, {node.y})"
              onmouseenter={() => handleNodeHover(node)}
              onmouseleave={handleNodeLeave}
              onclick={() => handleNodeClick(node)}
              style="cursor: pointer;"
              opacity={activeNode ? (isConnected ? 1 : 0.2) : 1}
            >
              <!-- Stippled halo -->
              {#if displayRadius > 4}
                <circle
                  r={displayRadius + 8}
                  fill={`url(#stipple-${node.type})`}
                  opacity={activeNode ? (isConnected ? 0.6 : 0.08) : 0.5}
                />
              {/if}
              <!-- Node circle with paper stroke for depth -->
              <circle
                r={displayRadius}
                fill={colorMap[node.type] || '#9A9285'}
                stroke={isPinned || isConnector ? '#2C2C2C' : (isConnected && !isActive ? '#2C2C2C' : '#FAF9F6')}
                stroke-width={isPinned || isConnector ? 3 : (isConnected && !isActive ? 1.5 : 1.5)}
                class="node-circle"
              />
              {#if node.type === 'minister' || baseRadius > 12 || isActive || isConnector}
                <text
                  y={displayRadius + 12}
                  text-anchor="middle"
                  class="node-label"
                  fill="#2C2C2C"
                  font-weight={isActive || isConnector ? '600' : '500'}
                  paint-order="stroke"
                  stroke="#FAF8F5"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  {node.name.length > 20 ? node.name.slice(0, 18) + '...' : node.name}
                </text>
              {/if}
            </g>
          {/if}
        {/each}
      </g>

      <!-- Leader line annotations — direct labels on the graph -->
      {#if simulationReady && !activeNode}
        <g class="annotations" opacity="0.7">
          {#if topBridge?.x}
            <line x1={topBridge.x} y1={topBridge.y - radiusScale(topBridge.total_value) - 8}
                  x2={topBridge.x + 30} y2={topBridge.y - radiusScale(topBridge.total_value) - 28}
                  stroke="#6b6b6b" stroke-width="0.75" stroke-dasharray="2,2"/>
            <circle cx={topBridge.x} cy={topBridge.y - radiusScale(topBridge.total_value) - 8}
                    r="2" fill="#C54B3C"/>
            <text x={topBridge.x + 33} y={topBridge.y - radiusScale(topBridge.total_value) - 30}
                  font-family="Satoshi, sans-serif" font-size="9" fill="#4a4a4a">
              Connects {topBridge.ministerCount} ministers
            </text>
            <text x={topBridge.x + 33} y={topBridge.y - radiusScale(topBridge.total_value) - 20}
                  font-family="Satoshi, sans-serif" font-size="8" fill="#6b6b6b" font-style="italic">
              {topBridge.name}
            </text>
          {/if}
          {#if largestDonor?.x && (!topBridge || largestDonor.id !== topBridge.id)}
            <line x1={largestDonor.x} y1={largestDonor.y + radiusScale(largestDonor.total_value) + 8}
                  x2={largestDonor.x - 25} y2={largestDonor.y + radiusScale(largestDonor.total_value) + 28}
                  stroke="#6b6b6b" stroke-width="0.75" stroke-dasharray="2,2"/>
            <circle cx={largestDonor.x} cy={largestDonor.y + radiusScale(largestDonor.total_value) + 8}
                    r="2" fill="#C54B3C"/>
            <text x={largestDonor.x - 28} y={largestDonor.y + radiusScale(largestDonor.total_value) + 32}
                  font-family="Satoshi, sans-serif" font-size="9" fill="#4a4a4a" text-anchor="end">
              {formatCurrency(largestDonor.total_value)} — largest donor
            </text>
          {/if}
        </g>
      {/if}
      <!-- Node detail as SVG annotation in corner of graph -->
      {#if activeNode}
        {@const donationLinks = processedLinks.filter(l =>
          (l.source?.id === activeNode.id || l.target?.id === activeNode.id) && l.link_type === 'donation'
        )}
        {@const meetingCount = activeNode.meeting_count || 0}
        {@const detailX = detailOnLeft ? -60 : width + 60}
        {@const anchor = detailOnLeft ? 'start' : 'end'}
        {@const position = activeNode.role
          ? activeNode.role
              .replace(/,\s*(Department\s+)?(for\s+)?[\w\s]+$/, '')
              .replace(/\s*\([^)]+\)\s*$/, '')
              .replace(/^The\s+/, '')
              .trim()
          : null}
        {@const profileUrl = activeNode.type === 'organization' ? `/organisation/${activeNode.id}` : `/person/${activeNode.id}`}
        {@const statsY = (position ? 32 : 18) + (activeNode.department ? 14 : 0) + 8}
        <g class="node-detail-annotation">
          <!-- Leader line from node to annotation corner -->
          <line x1={activeNode.x} y1={activeNode.y}
                x2={detailX} y2={-20}
                stroke="#6b6b6b" stroke-width="0.5" opacity="0.2" stroke-dasharray="3,3"/>
          <circle cx={activeNode.x} cy={activeNode.y} r="3" fill="#C54B3C" opacity="0.5"/>

          <!-- Type label -->
          <text x={detailX} y={-20} text-anchor={anchor}
                font-family="Satoshi, sans-serif" font-size="9" font-weight="600"
                fill="#C54B3C" style="text-transform:uppercase;letter-spacing:0.1em">
            {activeNode.type}
          </text>
          <!-- Name -->
          <text x={detailX} y={2} text-anchor={anchor}
                font-family="Zodiak, serif" font-size="18" font-weight="600" fill="#1a1a1a">
            {activeNode.name.length > 28 ? activeNode.name.slice(0, 26) + '…' : activeNode.name}
          </text>
          <!-- Role -->
          {#if position}
            <text x={detailX} y={18} text-anchor={anchor}
                  font-family="Satoshi, sans-serif" font-size="11" fill="#4a4a4a">
              {position.length > 40 ? position.slice(0, 38) + '…' : position}
            </text>
          {/if}
          {#if activeNode.department}
            <text x={detailX} y={position ? 32 : 18} text-anchor={anchor}
                  font-family="Satoshi, sans-serif" font-size="9" fill="#6b6b6b"
                  style="text-transform:uppercase;letter-spacing:0.05em">
              {activeNode.department.name}
            </text>
          {/if}

          <!-- Stats -->
          <line x1={detailOnLeft ? detailX : detailX - 180} y1={statsY}
                x2={detailOnLeft ? detailX + 180 : detailX} y2={statsY}
                stroke="#1a1a1a" stroke-width="0.5" opacity="0.1"/>
          {#if activeNode.total_value > 0}
            <text x={detailX} y={statsY + 18} text-anchor={anchor}
                  font-family="Zodiak, serif" font-size="16" font-weight="600" fill="#1a1a1a">
              {formatCurrency(activeNode.total_value)}
            </text>
            <text x={detailX} y={statsY + 30} text-anchor={anchor}
                  font-family="Satoshi, sans-serif" font-size="8" fill="#6b6b6b"
                  style="text-transform:uppercase;letter-spacing:0.05em">
              {activeNode.type === 'minister' ? 'received' : 'donated'}
            </text>
          {/if}

          <!-- Profile link -->
          <a href={profileUrl}>
            <text x={detailX} y={statsY + 48} text-anchor={anchor}
                  font-family="Satoshi, sans-serif" font-size="11" fill="#C54B3C"
                  style="cursor:pointer">
              View full profile →
            </text>
          </a>
        </g>
      {/if}
    </svg>


    <!-- Settings Panel -->
    <div class="settings-panel" class:open={showSettings}>
      <button class="settings-toggle" onclick={() => showSettings = !showSettings}>
        {showSettings ? 'Hide Settings' : 'Tweak Physics'}
      </button>
      
      {#if showSettings}
        <div class="settings-content">
          <div class="setting-group">
            <label>
              Global Repulsion: {chargeStrength}
              <input type="range" min="-500" max="-10" step="10" bind:value={chargeStrength} oninput={updatePhysics} />
            </label>
          </div>
          <div class="setting-group">
            <label>
              Minister Repulsion: {ministerCharge}
              <input type="range" min="-1000" max="-50" step="10" bind:value={ministerCharge} oninput={updatePhysics} />
            </label>
          </div>
          <div class="setting-group">
            <label>
              Donation Link Length: {linkDistance}
              <input type="range" min="50" max="400" step="10" bind:value={linkDistance} oninput={updatePhysics} />
            </label>
          </div>
          <div class="setting-group">
            <label>
              Role Link Length: {roleLinkDistance}
              <input type="range" min="10" max="150" step="5" bind:value={roleLinkDistance} oninput={updatePhysics} />
            </label>
          </div>
          <div class="setting-group">
            <label>
              Gravity X: {gravityX}
              <input type="range" min="0.01" max="1" step="0.01" bind:value={gravityX} oninput={updatePhysics} />
            </label>
          </div>
          <div class="setting-group">
            <label>
              Gravity Y: {gravityY}
              <input type="range" min="0.01" max="1" step="0.01" bind:value={gravityY} oninput={updatePhysics} />
            </label>
          </div>
          <div class="setting-group">
            <label>
              Collision Padding: {collisionPadding}
              <input type="range" min="0" max="20" step="1" bind:value={collisionPadding} oninput={updatePhysics} />
            </label>
          </div>
          <div class="setting-group">
            <label class="checkbox-label">
              <input type="checkbox" bind:checked={highlightBridges} />
              Highlight Key Connectors
            </label>
          </div>
        </div>
      {/if}
    </div>

    <!-- Legend -->
    <div class="legend">
      <div class="legend-item">
        <span class="legend-dot" style="background: #B85450;"></span>
        <span>Ministers ({stats.total_ministers})</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot" style="background: #5B7355;"></span>
        <span>Donors ({stats.total_donors || 0})</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot" style="background: #4A7BA7;"></span>
        <span>Directors</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot" style="background: #B87333;"></span>
        <span>PSCs (Significant Control)</span>
      </div>
      <div class="legend-item">
        <span class="legend-line"></span>
        <span>{stats.donation_connections || 0} donations</span>
      </div>
      {#if highlightBridges && bridgeNodeIds.size > 0}
        <div class="legend-item">
          <span class="legend-ring"></span>
          <span>Key Connectors ({bridgeNodeIds.size} connect 2+ ministers)</span>
        </div>
      {/if}
      {#if highlightBridges && corporateBridgeIds.size > 0}
        <div class="legend-item">
          <span class="legend-ring corporate"></span>
          <span>Corporate Bridges ({corporateBridgeIds.size} connect 2+ companies)</span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .minister-network {
    position: relative;
    width: 100%;
    overflow: visible;
  }

  .loading, .error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 600px;
  }

  .network-svg {
    width: 100%;
    height: auto;
    max-height: 80vh;
    overflow: visible;
  }

  .node-label {
    font-family: 'Satoshi', sans-serif;
    font-size: 11px;
    font-weight: 500;
    pointer-events: none;
  }

  .node-circle {
    transition: r 0.15s ease-out;
  }

  .node {
    transition: opacity 0.15s ease-out;
  }

  @media (prefers-reduced-motion: reduce) {
    .node-circle {
      transition: none;
    }
    .node {
      transition: none;
    }
  }

  .settings-panel {
    position: absolute;
    top: 20px;
    left: 20px;
    z-index: 100;
    font-family: 'Satoshi', sans-serif;
  }

  .settings-toggle {
    background: #FAF8F5;
    border: 1px solid #2C2C2C;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .settings-content {
    background: #FAF8F5;
    border: 1px solid #2C2C2C;
    padding: 16px;
    margin-top: 8px;
    width: 250px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }

  .setting-group {
    margin-bottom: 12px;
  }

  .setting-group:last-child {
    margin-bottom: 0;
  }

  .setting-group label {
    display: flex;
    flex-direction: column;
    font-size: 11px;
    font-weight: 500;
    color: #5A5A5A;
  }

  .setting-group input {
    margin-top: 4px;
    width: 100%;
  }

  .legend {
    position: absolute;
    bottom: 20px;
    left: 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-family: 'Satoshi', sans-serif;
    font-size: 11px;
    color: #5A5A5A;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .legend-line {
    width: 16px;
    height: 1px;
    background: #2C2C2C;
    opacity: 0.3;
  }

  .legend-ring {
    width: 12px;
    height: 12px;
    border: 3px solid rgba(218, 165, 32, 0.8);
    border-radius: 50%;
  }

  .legend-ring.corporate {
    border-color: rgba(91, 127, 149, 0.8);
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }

  .checkbox-label input {
    cursor: pointer;
  }
</style>
