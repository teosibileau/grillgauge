"""Sparkline renderable that always scales from 0°C baseline."""

from collections.abc import Sequence
from typing import TypeVar

from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style
from textual.renderables._blend_colors import blend_colors
from textual.renderables.sparkline import Sparkline as SparklineRenderable

T = TypeVar("T", int, float)


class ZeroBaselineSparklineRenderable(SparklineRenderable[T]):
    """Sparkline renderable that always scales from 0°C baseline.

    This renderable ensures temperature sparklines always scale from 0°C
    as the minimum, regardless of the actual temperature data range.
    This provides consistent, intuitive scaling for temperature monitoring.
    """

    def __init__(
        self, data: Sequence[T], *, summary: str | None = None, **kwargs
    ) -> None:
        """Initialize the renderable.

        Args:
            data: The data to render
            summary: Optional summary text to display below the sparkline
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(data, **kwargs)
        self.summary = summary

    def _calculate_layout(self, height: int) -> tuple[int, int | None, int | None]:
        """Calculate bar height, summary line, and spacer line for given height."""
        bar_height = height - 1 if (self.summary and height > 1) else height
        summary_line = height - 1 if (self.summary and height > 1) else None
        spacer_line = None
        return bar_height, summary_line, spacer_line

    def _render_empty_sparkline(self, width: int, height: int) -> RenderResult:
        """Render empty sparkline."""
        for _ in range(height - 1):
            yield Segment.line()
        yield Segment("▁" * width, self.min_color)

    def _render_single_data_point(self, width: int, height: int) -> RenderResult:
        """Render single data point sparkline."""
        for i in range(height):
            if i == height - 1 and self.summary and height > 1:
                # Render summary on last line
                yield Segment(self.summary.center(width), self.min_color)
            else:
                yield Segment("█" * width, self.max_color)
            if i < height - 1:
                yield Segment.line()

    def _render_multi_data_lines(
        self,
        width: int,
        height: int,
        bar_height: int,
        summary_line: int | None,
        spacer_line: int | None,
    ) -> RenderResult:
        """Render multi-data sparkline lines."""
        bar_line_segments = len(self.BARS)
        bar_segments = bar_line_segments * bar_height - 1

        # FORCE MINIMUM TO 0°C - This is the key difference from parent class
        minimum, maximum = 0, max(self.data)  # Always scale from 0°C
        extent = maximum - minimum or 1

        summary_function = self.summary_function
        min_color, max_color = self.min_color.color, self.max_color.color
        if min_color is None or max_color is None:
            msg = "min_color and max_color must not be None"
            raise ValueError(msg)

        buckets = tuple(self._buckets(list(self.data), num_buckets=width))

        # Render each line
        for i in range(height):
            if summary_line is not None and i == summary_line:
                # Render summary text with brighter color
                yield Segment(self.summary.center(width), self.max_color)
            else:
                # Render sparkline bars
                bar_line_index = (
                    height - 1 - i
                )  # Map i to bar line index (0 = bottom, bar_height-1 = top)
                current_bar_part_low = bar_line_index * bar_line_segments
                current_bar_part_high = (bar_line_index + 1) * bar_line_segments

                bucket_index = 0.0
                bars_rendered = 0
                step = len(buckets) / width

                while bars_rendered < width:
                    partition = buckets[int(bucket_index)]
                    partition_summary = summary_function(partition)
                    height_ratio = (partition_summary - minimum) / extent
                    bar_index = int(height_ratio * bar_segments)

                    # Determine bar character and color
                    if bar_index < current_bar_part_low:
                        bar, style = " ", None
                    elif bar_index >= current_bar_part_high:
                        bar_color = blend_colors(min_color, max_color, height_ratio)
                        bar, style = "█", Style.from_color(bar_color)
                    else:
                        bar = self.BARS[bar_index % bar_line_segments]
                        bar_color = blend_colors(min_color, max_color, height_ratio)
                        style = Style.from_color(bar_color)

                    yield Segment(bar, style)
                    bars_rendered += 1
                    bucket_index += step

            if i < height - 1:
                yield Segment.line()

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render sparkline with forced 0°C minimum scaling and optional summary."""
        width = self.width or options.max_width
        height = self.height or 1

        len_data = len(self.data)
        if len_data == 0:
            yield from self._render_empty_sparkline(width, height)
            return

        if len_data == 1:
            yield from self._render_single_data_point(width, height)
            return

        bar_height, summary_line, spacer_line = self._calculate_layout(height)
        yield from self._render_multi_data_lines(
            width, height, bar_height, summary_line, spacer_line
        )
