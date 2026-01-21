/**
 * ConcentrationChart - Visualizes donor concentration with D3.js
 * Shows inequality metrics (Gini, HHI) and top 10% vs bottom 90% comparison
 */

import React, { useRef, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as d3 from 'd3';
import { useConcentration } from '../hooks/useConcentration';
import { ConcentrationCategory } from '../types/concentration';
import styles from './ConcentrationChart.module.scss';

const queryClient = new QueryClient();

interface ConcentrationChartInnerProps {
  width?: number;
  height?: number;
}

export default function ConcentrationChart(props: ConcentrationChartInnerProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ConcentrationChartInner {...props} />
    </QueryClientProvider>
  );
}

function ConcentrationChartInner({
  width = 600,
  height = 300,
}: ConcentrationChartInnerProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data, isLoading, error, isFetching } = useConcentration();

  useEffect(() => {
    if (!data || !svgRef.current || data.concentration_category === 'no_data') return;

    // Clear previous chart
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current);
    const margin = { top: 40, right: 20, bottom: 60, left: 60 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Create main group
    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Prepare data for visualization
    const bottom90Share = 100 - data.top_10_percent_share;
    const chartData = [
      { label: 'Top 10%', value: data.top_10_percent_share, color: '#dc3545' },
      { label: 'Bottom 90%', value: bottom90Share, color: '#6c757d' },
    ];

    // Scales
    const x = d3
      .scaleBand()
      .domain(chartData.map((d) => d.label))
      .range([0, chartWidth])
      .padding(0.3);

    const y = d3
      .scaleLinear()
      .domain([0, 100])
      .range([chartHeight, 0]);

    // Bars
    g.selectAll('.bar')
      .data(chartData)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d) => x(d.label)!)
      .attr('y', (d) => y(d.value))
      .attr('width', x.bandwidth())
      .attr('height', (d) => chartHeight - y(d.value))
      .attr('fill', (d) => d.color);

    // Value labels on bars
    g.selectAll('.label')
      .data(chartData)
      .enter()
      .append('text')
      .attr('class', 'label')
      .attr('x', (d) => x(d.label)! + x.bandwidth() / 2)
      .attr('y', (d) => y(d.value) - 5)
      .attr('text-anchor', 'middle')
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text((d) => `${d.value.toFixed(1)}%`);

    // X-axis
    g.append('g')
      .attr('transform', `translate(0,${chartHeight})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .attr('font-size', '12px');

    // Y-axis
    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat((d) => `${d}%`))
      .selectAll('text')
      .attr('font-size', '12px');

    // Y-axis label
    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -margin.left + 15)
      .attr('x', -chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('fill', '#666')
      .text('Share of Total Donations');

    // Title
    svg
      .append('text')
      .attr('x', width / 2)
      .attr('y', 20)
      .attr('text-anchor', 'middle')
      .attr('font-size', '16px')
      .attr('font-weight', 'bold')
      .text('Donor Concentration Distribution');
  }, [data, width, height]);

  if (isLoading) {
    return (
      <div className={styles.chart}>
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.chart}>
        <div className="alert alert-danger" role="alert">
          Failed to load concentration metrics
        </div>
      </div>
    );
  }

  if (!data || data.concentration_category === 'no_data') {
    return (
      <div className={styles.chart}>
        <div className="alert alert-info" role="alert">
          No donation data available for selected filters
        </div>
      </div>
    );
  }

  const getCategoryLabel = (category: ConcentrationCategory): string => {
    switch (category) {
      case 'highly_concentrated':
        return 'Highly Concentrated';
      case 'moderately_concentrated':
        return 'Moderately Concentrated';
      case 'dispersed':
        return 'Dispersed';
      default:
        return 'Unknown';
    }
  };

  const getCategoryColor = (category: ConcentrationCategory): string => {
    switch (category) {
      case 'highly_concentrated':
        return 'danger';
      case 'moderately_concentrated':
        return 'warning';
      case 'dispersed':
        return 'success';
      default:
        return 'secondary';
    }
  };

  return (
    <div className={styles.chart}>
      <div className={styles.svgContainer}>
        <svg ref={svgRef} width={width} height={height} />
        {isFetching && (
          <div className={styles.fetchingIndicator}>
            <div className="spinner-border spinner-border-sm" role="status">
              <span className="visually-hidden">Updating...</span>
            </div>
          </div>
        )}
      </div>

      <div className={styles.metrics}>
        <div className="row g-3">
          <div className="col-md-3">
            <div className={styles.metric}>
              <div className={styles.metricLabel}>Gini Coefficient</div>
              <div className={styles.metricValue}>{data.gini_coefficient.toFixed(3)}</div>
              <div className={styles.metricHint}>0 = equal, 1 = unequal</div>
            </div>
          </div>

          <div className="col-md-3">
            <div className={styles.metric}>
              <div className={styles.metricLabel}>HHI</div>
              <div className={styles.metricValue}>{data.herfindahl_index.toFixed(3)}</div>
              <div className={styles.metricHint}>0 = dispersed, 1 = monopoly</div>
            </div>
          </div>

          <div className="col-md-3">
            <div className={styles.metric}>
              <div className={styles.metricLabel}>Top Donor Share</div>
              <div className={styles.metricValue}>{data.top_donor_share.toFixed(1)}%</div>
              <div className={styles.metricHint}>Largest single donor</div>
            </div>
          </div>

          <div className="col-md-3">
            <div className={styles.metric}>
              <div className={styles.metricLabel}>Category</div>
              <div className={styles.metricValue}>
                <span className={`badge bg-${getCategoryColor(data.concentration_category)}`}>
                  {getCategoryLabel(data.concentration_category)}
                </span>
              </div>
              <div className={styles.metricHint}>
                {data.total_donors.toLocaleString()} donors
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
