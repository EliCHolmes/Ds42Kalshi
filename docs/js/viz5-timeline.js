/*
 * Viz 5: Interactive Trade Timeline Explorer (D3)
 * Scatter plot of individual trades over time.
 * Shape = market_topic, size = trade value, brush+zoom, trend line.
 */

(function () {
  const margin = { top: 40, right: 30, bottom: 50, left: 70 };
  const width = 800 - margin.left - margin.right;
  const height = 480 - margin.top - margin.bottom;

  const topicShapes = {
    "Government Shutdown": d3.symbolCircle,
    "Elections & Nominations": d3.symbolTriangle,
    "International Affairs": d3.symbolSquare,
    "Executive Orders & Policy": d3.symbolDiamond,
    "Media & Mentions": d3.symbolStar,
    "Legal & Investigations": d3.symbolCross,
    "Other Political": d3.symbolWye,
  };

  const topicColors = {
    "Government Shutdown": "#4477AA",
    "Elections & Nominations": "#EE6677",
    "International Affairs": "#228833",
    "Executive Orders & Policy": "#CCBB44",
    "Media & Mentions": "#66CCEE",
    "Legal & Investigations": "#AA3377",
    "Other Political": "#BBBBBB",
  };

  const container = d3.select("#viz5");
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
    .attr("y", 20)
    .attr("text-anchor", "middle")
    .attr("font-size", "15px")
    .attr("font-weight", "bold")
    .text("Trade Timeline: Individual Trades Over Time by Topic");

  const tooltip = container
    .append("div")
    .attr("class", "d3-tooltip")
    .style("opacity", 0);

  d3.json("data/kalshi_trades.json").then(function (raw) {
    const data = raw.map((d) => ({
      date: new Date(d.t),
      value: d.v,
      count: d.c,
      topic: d.tp,
      title: d.ti,
      side: d.s,
    }));

    const x = d3.scaleTime().domain(d3.extent(data, (d) => d.date)).range([0, width]);
    const y = d3.scaleLog().domain([2000, d3.max(data, (d) => d.value) * 1.1]).range([height, 0]).clamp(true);
    const sizeScale = d3.scaleSqrt().domain(d3.extent(data, (d) => d.count)).range([12, 80]);

    const xAxis = g
      .append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(8).tickFormat(d3.timeFormat("%b %d")));

    xAxis
      .append("text")
      .attr("x", width / 2)
      .attr("y", 38)
      .attr("fill", "#333")
      .attr("text-anchor", "middle")
      .attr("font-size", "13px")
      .text("Date");

    g.append("g")
      .call(d3.axisLeft(y).ticks(5, "$,.0f"))
      .append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -height / 2)
      .attr("y", -55)
      .attr("fill", "#333")
      .attr("text-anchor", "middle")
      .attr("font-size", "13px")
      .text("Trade Value (USD)");

    const clip = svg
      .append("defs")
      .append("clipPath")
      .attr("id", "clip-timeline")
      .append("rect")
      .attr("width", width)
      .attr("height", height);

    const plotArea = g.append("g").attr("clip-path", "url(#clip-timeline)");

    // Trend line (linear regression in log space)
    const xVals = data.map((d) => d.date.getTime());
    const yVals = data.map((d) => Math.log(d.value));
    const n = xVals.length;
    const xMean = d3.mean(xVals);
    const yMean = d3.mean(yVals);
    const slope =
      d3.sum(xVals.map((xi, i) => (xi - xMean) * (yVals[i] - yMean))) /
      d3.sum(xVals.map((xi) => (xi - xMean) ** 2));
    const intercept = yMean - slope * xMean;

    const xExtent = d3.extent(data, (d) => d.date);
    const trendData = [
      { x: xExtent[0], y: Math.exp(intercept + slope * xExtent[0].getTime()) },
      { x: xExtent[1], y: Math.exp(intercept + slope * xExtent[1].getTime()) },
    ];

    const trendLine = plotArea
      .append("line")
      .attr("x1", x(trendData[0].x))
      .attr("y1", y(trendData[0].y))
      .attr("x2", x(trendData[1].x))
      .attr("y2", y(trendData[1].y))
      .attr("stroke", "#AA3377")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "6,3")
      .attr("opacity", 0.7);

    const points = plotArea
      .selectAll(".trade-point")
      .data(data)
      .join("path")
      .attr("class", "trade-point")
      .attr(
        "d",
        (d) =>
          d3.symbol().type(topicShapes[d.topic] || d3.symbolCircle).size(sizeScale(d.count))()
      )
      .attr("transform", (d) => `translate(${x(d.date)},${y(d.value)})`)
      .attr("fill", (d) => topicColors[d.topic] || "#999")
      .attr("opacity", 0.55)
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.5)
      .on("mouseover", function (event, d) {
        d3.select(this).attr("opacity", 1).attr("stroke-width", 2);
        tooltip.transition().duration(100).style("opacity", 0.95);
        tooltip
          .html(
            `<strong>${d.title}</strong><br/>` +
              `Topic: ${d.topic}<br/>` +
              `Value: $${d.value.toLocaleString()}<br/>` +
              `Contracts: ${d.count}<br/>` +
              `Side: ${d.side}<br/>` +
              `Date: ${d3.timeFormat("%b %d, %Y %I:%M %p")(d.date)}`
          )
          .style("left", event.pageX + 12 + "px")
          .style("top", event.pageY - 10 + "px");
      })
      .on("mouseout", function () {
        d3.select(this).attr("opacity", 0.55).attr("stroke-width", 0.5);
        tooltip.transition().duration(200).style("opacity", 0);
      });

    // Brush for zoom
    const brush = d3.brushX().extent([
      [0, 0],
      [width, height],
    ]).on("end", brushed);

    g.append("g").attr("class", "brush").call(brush);

    function brushed(event) {
      if (!event.selection) {
        x.domain(d3.extent(data, (d) => d.date));
      } else {
        const [x0, x1] = event.selection.map(x.invert);
        x.domain([x0, x1]);
        g.select(".brush").call(brush.move, null);
      }
      xAxis.transition().duration(500).call(d3.axisBottom(x).ticks(8).tickFormat(d3.timeFormat("%b %d")));
      points
        .transition()
        .duration(500)
        .attr("transform", (d) => `translate(${x(d.date)},${y(d.value)})`);

      const newExtent = x.domain();
      const newTrend = [
        { x: newExtent[0], y: Math.exp(intercept + slope * newExtent[0].getTime()) },
        { x: newExtent[1], y: Math.exp(intercept + slope * newExtent[1].getTime()) },
      ];
      trendLine
        .transition()
        .duration(500)
        .attr("x1", x(newTrend[0].x))
        .attr("y1", y(newTrend[0].y))
        .attr("x2", x(newTrend[1].x))
        .attr("y2", y(newTrend[1].y));
    }

    // Double-click to reset
    svg.on("dblclick", function () {
      x.domain(d3.extent(data, (d) => d.date));
      xAxis.transition().duration(500).call(d3.axisBottom(x).ticks(8).tickFormat(d3.timeFormat("%b %d")));
      points
        .transition()
        .duration(500)
        .attr("transform", (d) => `translate(${x(d.date)},${y(d.value)})`);
      trendLine
        .transition()
        .duration(500)
        .attr("x1", x(trendData[0].x))
        .attr("y1", y(trendData[0].y))
        .attr("x2", x(trendData[1].x))
        .attr("y2", y(trendData[1].y));
    });

    // Legend
    const legend = svg
      .append("g")
      .attr("transform", `translate(${margin.left + 10}, ${margin.top + 10})`);

    const topics = Object.keys(topicShapes);
    topics.forEach((topic, i) => {
      const row = legend
        .append("g")
        .attr("transform", `translate(0, ${i * 20})`);
      row
        .append("path")
        .attr("d", d3.symbol().type(topicShapes[topic]).size(60)())
        .attr("fill", topicColors[topic])
        .attr("transform", "translate(8, 0)");
      row
        .append("text")
        .attr("x", 20)
        .attr("y", 4)
        .attr("font-size", "11px")
        .attr("fill", "#333")
        .text(topic);
    });
  });
})();
