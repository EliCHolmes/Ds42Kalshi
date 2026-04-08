/*
 * Viz 7: Trade Activity Heatmap – Day of Week × Hour (D3)
 * Sequential single-hue (blues) encoding total trade volume.
 */

(function () {
  const margin = { top: 50, right: 120, bottom: 50, left: 100 };
  const cellSize = 28;
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const hours = d3.range(0, 24);
  const width = hours.length * cellSize;
  const height = days.length * cellSize;

  const container = d3.select("#viz7");

  const svg = container
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);

  const g = svg
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  svg
    .append("text")
    .attr("x", (width + margin.left + margin.right) / 2)
    .attr("y", 22)
    .attr("text-anchor", "middle")
    .attr("font-size", "15px")
    .attr("font-weight", "bold")
    .text("When Do High-Value Political Trades Happen?");

  const tooltip = container
    .append("div")
    .attr("class", "d3-tooltip")
    .style("opacity", 0);

  d3.json("data/kalshi_trades.json").then(function (raw) {
    const grid = {};
    days.forEach((d) => {
      hours.forEach((h) => {
        grid[`${d}-${h}`] = { day: d, hour: h, volume: 0, count: 0 };
      });
    });

    raw.forEach((d) => {
      const key = `${d.dw}-${d.h}`;
      if (grid[key]) {
        grid[key].volume += d.v;
        grid[key].count += 1;
      }
    });

    const cells = Object.values(grid);
    const maxVol = d3.max(cells, (d) => d.volume);

    const color = d3
      .scaleSequential(d3.interpolateBlues)
      .domain([0, maxVol]);

    const xScale = d3.scaleBand().domain(hours).range([0, width]).padding(0.05);
    const yScale = d3.scaleBand().domain(days).range([0, height]).padding(0.05);

    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(
        d3.axisBottom(xScale).tickFormat((h) => {
          if (h === 0) return "12am";
          if (h === 12) return "12pm";
          if (h < 12) return h + "am";
          return (h - 12) + "pm";
        })
      )
      .selectAll("text")
      .attr("font-size", "10px")
      .attr("transform", "rotate(-45)")
      .attr("text-anchor", "end");

    g.append("g").call(d3.axisLeft(yScale).tickFormat((d) => d.slice(0, 3)));

    g.append("text")
      .attr("x", width / 2)
      .attr("y", height + 45)
      .attr("text-anchor", "middle")
      .attr("font-size", "13px")
      .attr("fill", "#333")
      .text("Hour of Day (ET)");

    g.selectAll(".heatcell")
      .data(cells)
      .join("rect")
      .attr("class", "heatcell")
      .attr("x", (d) => xScale(d.hour))
      .attr("y", (d) => yScale(d.day))
      .attr("width", xScale.bandwidth())
      .attr("height", yScale.bandwidth())
      .attr("fill", (d) => (d.volume === 0 ? "#f0f0f0" : color(d.volume)))
      .attr("rx", 3)
      .on("mouseover", function (event, d) {
        d3.select(this).attr("stroke", "#333").attr("stroke-width", 2);
        tooltip.transition().duration(100).style("opacity", 0.95);
        const hourLabel = d.hour === 0 ? "12am" : d.hour === 12 ? "12pm" : d.hour < 12 ? d.hour + "am" : (d.hour - 12) + "pm";
        tooltip
          .html(
            `<strong>${d.day} ${hourLabel} ET</strong><br/>` +
              `Volume: $${d.volume.toLocaleString()}<br/>` +
              `Trades: ${d.count}`
          )
          .style("left", event.pageX + 12 + "px")
          .style("top", event.pageY - 10 + "px");
      })
      .on("mouseout", function () {
        d3.select(this).attr("stroke", "none");
        tooltip.transition().duration(200).style("opacity", 0);
      });

    // Color legend
    const legendWidth = 15;
    const legendHeight = height;
    const legendG = svg
      .append("g")
      .attr(
        "transform",
        `translate(${margin.left + width + 20},${margin.top})`
      );

    const legendScale = d3.scaleLinear().domain([0, maxVol]).range([legendHeight, 0]);

    const defs = svg.append("defs");
    const gradient = defs
      .append("linearGradient")
      .attr("id", "heatmap-gradient")
      .attr("x1", "0%")
      .attr("y1", "100%")
      .attr("x2", "0%")
      .attr("y2", "0%");
    gradient
      .append("stop")
      .attr("offset", "0%")
      .attr("stop-color", d3.interpolateBlues(0));
    gradient
      .append("stop")
      .attr("offset", "100%")
      .attr("stop-color", d3.interpolateBlues(1));

    legendG
      .append("rect")
      .attr("width", legendWidth)
      .attr("height", legendHeight)
      .style("fill", "url(#heatmap-gradient)");

    legendG
      .append("g")
      .attr("transform", `translate(${legendWidth},0)`)
      .call(
        d3.axisRight(legendScale).ticks(5).tickFormat(d3.format("$,.0f"))
      );

    legendG
      .append("text")
      .attr("x", legendWidth / 2)
      .attr("y", -8)
      .attr("text-anchor", "middle")
      .attr("font-size", "11px")
      .attr("fill", "#333")
      .text("Volume");
  });
})();
