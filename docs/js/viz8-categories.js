/*
 * Viz 8: Market Category Breakdown (D3)
 * Grouped bar chart: volume and trade count by market_topic.
 * Hover tooltip with details.
 */

(function () {
  const margin = { top: 50, right: 30, bottom: 120, left: 80 };
  const width = 750 - margin.left - margin.right;
  const height = 460 - margin.top - margin.bottom;

  const container = d3.select("#viz8");

  const metricControls = container.append("div").attr("class", "viz-controls");
  metricControls
    .append("label")
    .style("font-weight", "bold")
    .style("margin-right", "8px")
    .text("Metric:");

  const metricSelect = metricControls.append("select").attr("id", "metric-select");
  metricSelect.append("option").attr("value", "volume").text("Total Volume (USD)");
  metricSelect.append("option").attr("value", "count").text("Number of Trades");
  metricSelect.append("option").attr("value", "avg").text("Avg Trade Size (USD)");

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

  const topicColors = {
    "Government Shutdown": "#4477AA",
    "Elections & Nominations": "#EE6677",
    "International Affairs": "#228833",
    "Executive Orders & Policy": "#CCBB44",
    "Media & Mentions": "#66CCEE",
    "Legal & Investigations": "#AA3377",
    "Other Political": "#BBBBBB",
  };

  d3.json("data/kalshi_trades.json").then(function (raw) {
    const byTopic = d3.rollup(
      raw,
      (v) => ({
        volume: d3.sum(v, (d) => d.v),
        count: v.length,
        avg: d3.mean(v, (d) => d.v),
        uniqueMarkets: new Set(v.map((d) => d.tk)).size,
      }),
      (d) => d.tp
    );

    const data = Array.from(byTopic, ([topic, vals]) => ({
      topic,
      volume: vals.volume,
      count: vals.count,
      avg: vals.avg,
      uniqueMarkets: vals.uniqueMarkets,
    })).sort((a, b) => b.volume - a.volume);

    const x = d3.scaleBand().domain(data.map((d) => d.topic)).range([0, width]).padding(0.25);
    const y = d3.scaleLinear().range([height, 0]);

    const xAxisG = g.append("g").attr("transform", `translate(0,${height})`);
    const yAxisG = g.append("g");
    const yLabel = g
      .append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -height / 2)
      .attr("y", -60)
      .attr("fill", "#333")
      .attr("text-anchor", "middle")
      .attr("font-size", "13px");

    function update(metric) {
      const getValue = (d) =>
        metric === "volume" ? d.volume : metric === "count" ? d.count : d.avg;
      const formatVal = (v) =>
        metric === "count"
          ? v.toLocaleString()
          : "$" + v.toLocaleString(undefined, { maximumFractionDigits: 0 });

      const titles = {
        volume: "Total Trade Volume by Market Category",
        count: "Number of Trades by Market Category",
        avg: "Average Trade Size by Market Category",
      };
      const yLabels = {
        volume: "Total Volume (USD)",
        count: "Number of Trades",
        avg: "Avg Trade Size (USD)",
      };

      chartTitle.text(titles[metric]);
      yLabel.text(yLabels[metric]);

      y.domain([0, d3.max(data, getValue) * 1.1]);

      xAxisG
        .transition()
        .duration(400)
        .call(d3.axisBottom(x))
        .selectAll("text")
        .attr("transform", "rotate(-30)")
        .attr("text-anchor", "end")
        .attr("font-size", "11px");

      yAxisG
        .transition()
        .duration(400)
        .call(
          d3
            .axisLeft(y)
            .ticks(6)
            .tickFormat(metric === "count" ? d3.format(",") : d3.format("$,.0f"))
        );

      const bars = g.selectAll(".cat-bar").data(data, (d) => d.topic);
      bars
        .join(
          (enter) =>
            enter
              .append("rect")
              .attr("class", "cat-bar")
              .attr("x", (d) => x(d.topic))
              .attr("y", height)
              .attr("width", x.bandwidth())
              .attr("height", 0)
              .attr("fill", (d) => topicColors[d.topic] || "#999")
              .attr("rx", 3),
          (update) => update,
          (exit) => exit.remove()
        )
        .on("mouseover", function (event, d) {
          d3.select(this).attr("opacity", 0.8);
          tooltip.transition().duration(100).style("opacity", 0.95);
          tooltip
            .html(
              `<strong>${d.topic}</strong><br/>` +
                `Volume: $${d.volume.toLocaleString()}<br/>` +
                `Trades: ${d.count.toLocaleString()}<br/>` +
                `Avg Size: $${d.avg.toLocaleString(undefined, { maximumFractionDigits: 0 })}<br/>` +
                `Unique Markets: ${d.uniqueMarkets}`
            )
            .style("left", event.pageX + 12 + "px")
            .style("top", event.pageY - 10 + "px");
        })
        .on("mouseout", function () {
          d3.select(this).attr("opacity", 1);
          tooltip.transition().duration(200).style("opacity", 0);
        })
        .transition()
        .duration(500)
        .attr("x", (d) => x(d.topic))
        .attr("y", (d) => y(getValue(d)))
        .attr("width", x.bandwidth())
        .attr("height", (d) => height - y(getValue(d)));

      const labels = g.selectAll(".bar-label").data(data, (d) => d.topic);
      labels
        .join(
          (enter) =>
            enter
              .append("text")
              .attr("class", "bar-label")
              .attr("text-anchor", "middle")
              .attr("font-size", "11px")
              .attr("fill", "#333"),
          (update) => update,
          (exit) => exit.remove()
        )
        .transition()
        .duration(500)
        .attr("x", (d) => x(d.topic) + x.bandwidth() / 2)
        .attr("y", (d) => y(getValue(d)) - 5)
        .text((d) => formatVal(getValue(d)));
    }

    update("volume");
    metricSelect.on("change", function () {
      update(this.value);
    });
  });
})();
