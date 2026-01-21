"""
Custom Wagtail StreamField blocks for embedding React islands in editorial content.

These blocks allow editors to embed interactive data visualizations and components
in Wagtail pages without writing code.
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class TopDonorsLeaderboardBlock(blocks.StructBlock):
    """
    Embed an interactive top donors leaderboard.

    Displays a ranked list of top donors with filtering capabilities.
    Syncs with FilterPanel if present on the page.
    """
    title = blocks.CharBlock(
        default="Top Donors",
        help_text="Heading displayed above the leaderboard"
    )
    limit = blocks.IntegerBlock(
        default=10,
        min_value=5,
        max_value=50,
        help_text="Number of donors to display (5-50)"
    )
    show_filter_panel = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Show filter controls alongside the leaderboard"
    )

    class Meta:
        icon = 'list-ol'
        label = 'Top Donors Leaderboard'
        template = 'cms/blocks/top_donors_leaderboard.html'


class ConcentrationChartBlock(blocks.StructBlock):
    """
    Embed a donor concentration visualization chart.

    Displays Gini coefficient, HHI, and top 10% vs bottom 90% distribution.
    Automatically updates when filters change.
    """
    title = blocks.CharBlock(
        default="Donor Concentration",
        help_text="Heading displayed above the chart"
    )
    description = blocks.TextBlock(
        required=False,
        help_text="Optional explanatory text displayed below the chart"
    )

    class Meta:
        icon = 'snippet'
        label = 'Concentration Chart'
        template = 'cms/blocks/concentration_chart.html'


class FilterPanelBlock(blocks.StructBlock):
    """
    Embed interactive filter controls.

    Allows visitors to filter data by date range, donation amount, donor type, etc.
    All islands on the page will respond to filter changes.
    """
    title = blocks.CharBlock(
        default="Filters",
        help_text="Heading displayed above filters"
    )

    class Meta:
        icon = 'cog'
        label = 'Filter Panel'
        template = 'cms/blocks/filter_panel.html'


class ActorCardBlock(blocks.StructBlock):
    """
    Embed a data card for a political actor (person or organization).

    Displays name, classification, and optionally donation statistics.
    Can link to full profile page.
    """
    actor_id = blocks.IntegerBlock(
        help_text="Actor ID from the database (find in /django-admin/datafetch/actor/)"
    )
    compact = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Use compact single-line layout"
    )
    show_stats = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Show donation statistics"
    )

    class Meta:
        icon = 'user'
        label = 'Actor Card'
        template = 'cms/blocks/actor_card.html'


class StatsGridBlock(blocks.StructBlock):
    """
    Embed the homepage key metrics grid.

    Displays 4 key statistics: total donations, total value, concentration, and dual influence.
    Data is fetched live from the API with timestamp provenance.
    """
    title = blocks.CharBlock(
        required=False,
        help_text="Optional heading displayed above the metrics grid"
    )
    api_url = blocks.CharBlock(
        default="/api/v2/aggregates/stats/",
        help_text="API endpoint for statistics (usually leave as default)"
    )

    class Meta:
        icon = 'snippet'
        label = 'Key Metrics Grid'
        template = 'cms/blocks/stats_grid.html'


class PartyBreakdownBlock(blocks.StructBlock):
    """
    Embed party donation breakdown.

    Displays donation statistics by political party with official party colors.
    Shows total received, donor count, and average donation per party.
    """
    title = blocks.CharBlock(
        default="Donations by Party",
        help_text="Heading displayed above the party breakdown"
    )
    limit = blocks.IntegerBlock(
        default=10,
        min_value=3,
        max_value=20,
        help_text="Number of parties to display (3-20)"
    )
    compact = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Use compact layout (less detail)"
    )
    api_url = blocks.CharBlock(
        default="/api/v2/aggregates/party-donations/",
        help_text="API endpoint for party donations (usually leave as default)"
    )

    class Meta:
        icon = 'group'
        label = 'Party Breakdown'
        template = 'cms/blocks/party_breakdown.html'


class DataVisualizationBlock(blocks.StreamBlock):
    """
    Container block for data visualizations and interactive components.

    Allows editors to combine multiple islands on a single page.
    """
    stats_grid = StatsGridBlock()
    party_breakdown = PartyBreakdownBlock()
    leaderboard = TopDonorsLeaderboardBlock()
    concentration_chart = ConcentrationChartBlock()
    filter_panel = FilterPanelBlock()
    actor_card = ActorCardBlock()

    class Meta:
        icon = 'image'
        label = 'Data Visualization'
