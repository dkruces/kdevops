#!/usr/bin/env python3

import argparse
import os
import re
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from datetime import datetime
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


def human_format(num):
    """Format numbers in human-readable format (K, M, B, T)."""
    if num >= 1_000_000_000_000:
        return f"{num//1_000_000_000_000:,}T"
    elif num >= 1_000_000_000:
        return f"{num//1_000_000_000:,}B"
    elif num >= 1_000_000:
        return f"{num//1_000_000:,}M"
    elif num >= 1_000:
        return f"{num//1_000:,}K"
    return f"{num:,}"


def parse_nvme_smart_stats_file(filename):
    """Parse timestamped NVMe SMART stats file."""
    timestamps = []
    data_points = []

    with open(filename, "r") as f:
        content = f.read()

    # Split by timestamp pattern: YYYY-MM-DD HH:MM:SS
    entries = re.split(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)

    for i in range(1, len(entries), 2):
        if i + 1 < len(entries):
            timestamp_str = entries[i]
            json_block = entries[i + 1].strip()

            if not json_block:
                continue

            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                data = json.loads(json_block)

                # Skip error entries
                if "error" in data:
                    continue

                timestamps.append(timestamp)
                data_points.append(data)

            except (ValueError, json.JSONDecodeError) as e:
                print(f"Warning: Skipping malformed entry: {e}")
                continue

    return timestamps, data_points


def extract_metric_series(data_points, metric_key):
    """Extract time series for a specific metric."""
    values = []
    for data in data_points:
        if metric_key in data:
            values.append(data[metric_key])
        else:
            values.append(0)  # Default to 0 if metric missing
    return values


def plot_nvme_smart_stats(stats_files, output_file):
    """Plot unified NVMe SMART stats from multiple files."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Store data for A/B comparison analysis
    ab_data = []

    # Color mapping for multiple devices/hosts
    color_map = {}
    color_idx = 0

    for idx, file in enumerate(stats_files):
        # Extract device and host info from filename
        # Format: hostname_nvme_ocp_devicename_stats.txt
        base_name = os.path.splitext(os.path.basename(file))[0]
        name_parts = base_name.split("_")

        if len(name_parts) >= 4:
            hostname = name_parts[0]
            device = "_".join(name_parts[3:-1])  # Extract device name
            display_name = f"{hostname}:{device}"
        else:
            display_name = base_name

        # Determine if this is a dev node
        is_dev = "-dev" in display_name

        # Assign colors
        if display_name not in color_map:
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
            color_map[display_name] = colors[color_idx % len(colors)]
            color_idx += 1

        color = color_map[display_name]

        # Line style based on node type (dev vs baseline)
        if is_dev:
            linestyle = "--"  # Dashed for dev
            linewidth = 2.5
            alpha = 0.8
        else:
            linestyle = "-"  # Solid for baseline
            linewidth = 2.0
            alpha = 1.0

        timestamps, data_points = parse_nvme_smart_stats_file(file)

        if not data_points:
            continue

        # Convert to hours from start
        time_hours = list(range(len(data_points)))
        time_hours = [
            t * (300 / 3600) for t in time_hours
        ]  # Convert intervals to hours (default 5min intervals)

        # Extract key metrics from standard SMART log
        data_units_written = extract_metric_series(data_points, "data_units_written")
        data_units_read = extract_metric_series(data_points, "data_units_read")
        temperature = extract_metric_series(data_points, "temperature")
        percent_used = extract_metric_series(data_points, "percent_used")
        media_errors = extract_metric_series(data_points, "media_errors")
        power_cycles = extract_metric_series(data_points, "power_cycles")
        power_on_hours = extract_metric_series(data_points, "power_on_hours")
        unsafe_shutdowns = extract_metric_series(data_points, "unsafe_shutdowns")

        # Plot 1: Data Units (Written/Read)
        ax1.plot(
            time_hours,
            data_units_written,
            label=f"{display_name} (Written)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )
        ax1.plot(
            time_hours,
            data_units_read,
            label=f"{display_name} (Read)",
            color=color,
            linewidth=linewidth,
            linestyle=":",
            alpha=alpha * 0.8,
        )

        # Plot 2: Health Metrics (Temperature and Wear)
        ax2.plot(
            time_hours,
            temperature,
            label=f"{display_name} (Temperature)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )
        ax2_twin = ax2.twinx()
        ax2_twin.plot(
            time_hours,
            percent_used,
            label=f"{display_name} (Wear %)",
            color=color,
            linewidth=linewidth,
            linestyle="--",
            alpha=alpha * 0.7,
        )

        # Plot 3: Power and Thermal
        ax3.plot(
            time_hours,
            power_cycles,
            label=f"{display_name} (Power Cycles)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
            marker="o" if not is_dev else "^",
            markersize=4,
            markevery=max(1, len(time_hours) // 10),
        )

        # Plot 4: Reliability Metrics
        ax4.plot(
            time_hours,
            media_errors,
            label=f"{display_name} (Media Errors)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )
        ax4_twin = ax4.twinx()
        ax4_twin.plot(
            time_hours,
            unsafe_shutdowns,
            label=f"{display_name} (Unsafe Shutdowns)",
            color=color,
            linewidth=linewidth,
            linestyle="-.",
            alpha=alpha * 0.7,
        )

        # Store data for A/B comparison
        if len(stats_files) == 2:
            ab_data.append(
                {
                    "name": display_name,
                    "is_dev": is_dev,
                    "final_written": (
                        data_units_written[-1] if data_units_written else 0
                    ),
                    "final_read": data_units_read[-1] if data_units_read else 0,
                    "final_temperature": temperature[-1] if temperature else 0,
                    "final_wear_pct": percent_used[-1] if percent_used else 0,
                }
            )

    # Configure plots
    title_suffix = " (A/B Comparison)" if len(stats_files) == 2 else ""

    # Plot 1: Data Units
    ax1.set_title(f"NVMe Data Units Over Time{title_suffix}", fontsize=14)
    ax1.set_xlabel("Time (hours from start)", fontsize=12)
    ax1.set_ylabel("Data Units (512-byte blocks)", fontsize=12)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: human_format(int(x))))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best", fontsize=9)

    # Plot 2: Health Metrics
    ax2.set_title(f"NVMe Health and Temperature{title_suffix}", fontsize=14)
    ax2.set_xlabel("Time (hours from start)", fontsize=12)
    ax2.set_ylabel("Temperature (K)", fontsize=12, color="tab:blue")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left", fontsize=9)

    ax2_twin.set_ylabel("Wear Percentage (%)", fontsize=12, color="tab:orange")
    ax2_twin.legend(loc="upper right", fontsize=9)

    # Plot 3: Power Metrics
    ax3.set_title(f"NVMe Power Cycles{title_suffix}", fontsize=14)
    ax3.set_xlabel("Time (hours from start)", fontsize=12)
    ax3.set_ylabel("Power Cycles", fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="best", fontsize=9)

    # Plot 4: Reliability
    ax4.set_title(f"NVMe Reliability Metrics{title_suffix}", fontsize=14)
    ax4.set_xlabel("Time (hours from start)", fontsize=12)
    ax4.set_ylabel("Media Errors", fontsize=12, color="tab:red")
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc="upper left", fontsize=9)

    ax4_twin.set_ylabel("Unsafe Shutdowns", fontsize=12, color="tab:brown")
    ax4_twin.legend(loc="upper right", fontsize=9)

    # A/B Analysis Summary if applicable
    if len(ab_data) == 2:
        baseline = next((d for d in ab_data if not d["is_dev"]), ab_data[0])
        dev = next((d for d in ab_data if d["is_dev"]), ab_data[1])

        summary_text = (
            f"A/B Summary:\n"
            f"Written: {baseline['name']}: {human_format(baseline['final_written'])}, "
            f"{dev['name']}: {human_format(dev['final_written'])}\n"
            f"Temperature: {baseline['name']}: {baseline['final_temperature']}K, "
            f"{dev['name']}: {dev['final_temperature']}K\n"
            f"Wear: {baseline['name']}: {baseline['final_wear_pct']}%, "
            f"{dev['name']}: {dev['final_wear_pct']}%"
        )

        plt.figtext(
            0.02,
            0.02,
            summary_text,
            fontsize=9,
            ha="left",
            va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.8),
        )

    plt.suptitle(f"NVMe SMART Monitoring Results{title_suffix}", fontsize=16, y=0.98)
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Generated plot: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Plot NVMe SMART statistics")
    parser.add_argument("stats_files", nargs="+", help="NVMe SMART stats files to plot")
    parser.add_argument("-o", "--output", required=True, help="Output plot file (PNG)")

    args = parser.parse_args()

    # Validate input files
    valid_files = []
    for file in args.stats_files:
        if os.path.exists(file):
            valid_files.append(file)
        else:
            print(f"Warning: File {file} does not exist, skipping")

    if not valid_files:
        print("Error: No valid input files found")
        return 1

    try:
        plot_nvme_smart_stats(valid_files, args.output)
        return 0
    except Exception as e:
        print(f"Error generating plot: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
