/*
 * Viz 6: Market Deep Dive – Price & Volume Over Time (D3)
 * Dual-axis chart: line (implied probability) + bars (daily volume).
 * Dropdown to switch between market topics.
 */

(function () {
  const margin = { top: 50, right: 70, bottom: 50, left: 70 };
  const width = 800 - margin.left - margin.right;
  const height = 440 - margin.top - margin.bottom;

  const container = d3.select("#viz6");

  const controls = container.append("div").attr("class", "viz-controls");
  controls
    .append("label")
    .attr("for", "topic-select")
    .style("font-weight", "bold")
    .style("margin-right", "8px")
    .text("Select Topic:");

  const dropdown = controls.append("select").attr("id", "topic-select");

  const svg = container
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);

  const g = svg
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  const chartTitle = svg
    .append("text")
    .attr("x", (width + margin.left + margin.right) / 2)
    .attr("y", 22)
    .attr("text-anchor", "middle")
    .attr("font-size", "15px")
    .attr("font-weight", "bold");

  const tooltip = container
    .append("div")
    .attr("class", "d3-tooltip")
    .style("opacity", 0);

  d3.json("data/kalshi_trades.json").then(function (raw) {
    const parseDate = d3.timeParse("%Y-%m-%dT%H:%M:%S");
    const data = raw.map((d) => ({
      date: new Date(d.t),
      value: d.v,
      prob: d.p,
      topic: d.tp,
      title: d.ti,
      side: d.s,
    }));

    const topics = [...new Set(data.map((d) => d.topic))].sort();
    dropdown
      .selectAll("option")
      .data(topics)
      .join("option")
      .attr("value", (d) => d)
      .text((d) => d);

    dropdown.property("value", "Government Shutdown");

    function aggregateByDay(subset) {
      const byDay = d3.rollup(
        subset,
        (v) => ({
          volume: d3.sum(v, (d) => d.value),
          avgProb: d3.mean(v, (d) => d.prob),
          count: v.length,
        }),
        (d) => d3.timeDay(d.date)
      );
      return Array.from(byDay, ([date, vals]) => ({
        date,
        volume: vals.volume,
        avgProb: vals.avgProb,
        count: vals.count,
      })).sort((a, b) => a.date - b.date);
    }

    const x = d3.scaleTime().range([0, width]);
    const yVolume = d3.scaleLinear().range([height, 0]);
    const yProb = d3.scaleLinear().domain([0, 1]).range([height, 0]);

    const xAxisG = g
      .append("g")
      .attr("transform", `translate(0,${height})`);
    const yLeftG = g.append("g");
    const yRightG = g.append("g").attr("transform", `translate(${width},0)`);

    xAxisG
      .append("text")
      .attr("x", width / 2)
      .attr("y", 40)
      .attr("fill", "#333")
      .attr("text-anchor", "middle")
      .attr("font-size", "13px")
      .text("Date");

    yLeftG
      .append("text")
      .attr("class", "y-left-label")
      .attr("transform", "rotate(-90)")
      .attr("x", -height / 2)
      .attr("y", -55)
      .attr("fill", "#4477AA")
      .attr("text-anchor", "middle")
      .attr("font-size", "13px")
      .text("Daily Volume (USD)");

    yRightG
      .append("text")
      .attr("transform", "rotate(90)")
      .attr("x", height / 2)
      .attr("y", -55)
      .attr("fill", "#EE6677")
      .attr("text-anchor", "middle")
      .attr("font-size", "13px")
      .text("Avg Implied Probability");

    const barsG = g.append("g");
    const lineG = g.append("g");

    function update(topic) {
      const subset = data.filter((d) => d.topic === topic);
      const daily = aggregateByDay(subset);

      chartTitle.text(`Market Deep Dive: ${topic}`);

      x.domain(d3.extent(daily, (d) => d.date));
      yVolume.domain([0, d3.max(daily, (d) => d.volume) * 1.1]);

      xAxisG
        .transition()
        .duration(500)
        .call(d3.axisBottom(x).ticks(8).tickFormat(d3.timeFormat("%b %d")));
      yLeftG
        .transition()
        .duration(500)
        .call(d3.axisLeft(yVolume).ticks(6).tickFormat(d3.format("$,.0f")));
      yRightG
        .transition()
        .duration(500)
        .call(d3.axisRight(yProb).ticks(5).tickFormat(d3.format(".0%")));

      const barWidth = Math.max(2, width / daily.length - 2);

      const bars = barsG.selectAll(".vol-bar").data(daily, (d) => d.date);
      bars
        .join(
          (enter) =>
            enter
              .append("rect")
              .attr("class", "vol-bar")
              .attr("x", (d) => x(d.date) - barWidth / 2)
              .attr("y", height)
              .attr("width", barWidth)
              .attr("height", 0)
              .attr("fill", "#4477AA")
              .attr("opacity", 0.5),
          (update) => update,
          (exit) => exit.transition().duration(300).attr("height", 0).attr("y", height).remove()
        )
        .on("mouseover", function (event, d) {
          d3.select(this).attr("opacity", 0.8);
          tooltip.transition().duration(100).style("opacity", 0.95);
          tooltip
            .html(
              `<strong>${d3.timeFormat("%b %d, %Y")(d.date)}</strong><br/>` +
                `Volume: $${d.volume.toLocaleString()}<br/>` +
                `Avg Prob: ${(d.avgProb * 100).toFixed(1)}%<br/>` +
                `Trades: ${d.count}`
            )
            .style("left", event.pageX + 12 + "px")
            .style("top", event.pageY - 10 + "px");
        })
        .on("mouseout", function () {
          d3.select(this).attr("opacity", 0.5);
          tooltip.transition().duration(200).style("opacity", 0);
        })
        .transition()
        .duration(500)
        .attr("x", (d) => x(d.date) - barWidth / 2)
        .attr("y", (d) => yVolume(d.volume))
        .attr("width", barWidth)
        .attr("height", (d) => height - yVolume(d.volume));

      const line = d3
        .line()
        .x((d) => x(d.date))
        .y((d) => yProb(d.avgProb))
        .curve(d3.curveMonotoneX);

      const linePath = lineG.selectAll(".prob-line").data([daily]);
      linePath
        .join(
          (enter) =>
            enter
              .append("path")
              .attr("class", "prob-line")
              .attr("fill", "none")
              .attr("stroke", "#EE6677")
              .attr("stroke-width", 2.5)
              .attr("d", line),
          (update) => update.transition().duration(500).attr("d", line),
          (exit) => exit.remove()
        );

      const dots = lineG.selectAll(".prob-dot").data(daily, (d) => d.date);
      dots
        .join(
          (enter) =>
            enter
              .append("circle")
              .attr("class", "prob-dot")
              .attr("r", 4)
              .attr("fill", "#EE6677")
              .attr("stroke", "#fff")
              .attr("stroke-width", 1.5)
              .attr("cx", (d) => x(d.date))
              .attr("cy", (d) => yProb(d.avgProb)),
          (update) =>
            update
              .transition()
              .duration(500)
              .attr("cx", (d) => x(d.date))
              .attr("cy", (d) => yProb(d.avgProb)),
          (exit) => exit.remove()
        )
        .on("mouseover", function (event, d) {
          d3.select(this).attr("r", 6);
          tooltip.transition().duration(100).style("opacity", 0.95);
          tooltip
            .html(
              `<strong>${d3.timeFormat("%b %d, %Y")(d.date)}</strong><br/>` +
                `Avg Implied Prob: ${(d.avgProb * 100).toFixed(1)}%`
            )
            .style("left", event.pageX + 12 + "px")
            .style("top", event.pageY - 10 + "px");
        })
        .on("mouseout", function () {
          d3.select(this).attr("r", 4);
          tooltip.transition().duration(200).style("opacity", 0);
        });
    }

    update("Government Shutdown");
    dropdown.on("change", function () {
      update(this.value);
    });
  });
})();
