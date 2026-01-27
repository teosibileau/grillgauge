"""Sparkline renderable that always scales from 0°C baseline."""

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

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render sparkline with forced 0°C minimum scaling."""
        width = self.width or options.max_width
        height = self.height or 1

        len_data = len(self.data)
        if len_data == 0:
            for _ in range(height - 1):
                yield Segment.line()

            yield Segment("▁" * width, self.min_color)
            return
        if len_data == 1:
            for i in range(height):
                yield Segment("█" * width, self.max_color)

                if i < height - 1:
                    yield Segment.line()
            return

        bar_line_segments = len(self.BARS)
        bar_segments = bar_line_segments * height - 1

        # FORCE MINIMUM TO 0°C - This is the key difference from parent class
        minimum, maximum = 0, max(self.data)  # Always scale from 0°C
        extent = maximum - minimum or 1

        summary_function = self.summary_function
        min_color, max_color = self.min_color.color, self.max_color.color
        if min_color is None or max_color is None:
            msg = "min_color and max_color must not be None"
            raise ValueError(msg)

        buckets = tuple(self._buckets(list(self.data), num_buckets=width))

        # Render each line of the sparkline
        for i in reversed(range(height)):
            current_bar_part_low = i * bar_line_segments
            current_bar_part_high = (i + 1) * bar_line_segments

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

            if i > 0:
                yield Segment.line()
