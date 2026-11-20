package web

import (
	"fmt"
	"html"
	"html/template"
	"math"
	"strings"
)

type barPoint struct {
	Label      string
	Hover      string
	Value      float64
	Text       string
	Incomplete bool
}

func niceStep(value float64) float64 {
	if value <= 0 {
		return 0.25
	}
	magnitude := math.Pow(10, math.Floor(math.Log10(value)))
	for _, multiple := range []float64{1, 2, 5, 10} {
		if value <= multiple*magnitude*(1+1e-9) {
			return multiple * magnitude
		}
	}
	return 10 * magnitude
}

func barPath(x, y, w, h float64) string {
	r := math.Min(3, math.Min(w/2, h))
	return fmt.Sprintf("M%.1f %.1fV%.1fQ%.1f %.1f %.1f %.1fH%.1fQ%.1f %.1f %.1f %.1fV%.1fZ",
		x, y+h, y+r, x, y, x+r, y, x+w-r, x+w, y, x+w, y+r, y+h)
}

const minIncompleteHeight = 6.0

func barChart(id, title string, points []barPoint, tick func(float64) string) template.HTML {
	const (
		width, height      = 760.0, 220.0
		left, right        = 56.0, 8.0
		top, bottom        = 12.0, 34.0
		plotW, plotH       = width - left - right, height - top - bottom
		gridLines          = 4
		maxLabels          = 10
		minBarGap, barFrac = 1.0, 0.72
	)
	maxValue := 0.0
	for _, point := range points {
		maxValue = math.Max(maxValue, point.Value)
	}
	yMax := niceStep(maxValue/gridLines) * gridLines

	var svg strings.Builder
	fmt.Fprintf(&svg, `<svg class="chart" viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">`, width, height, html.EscapeString(title))
	fmt.Fprintf(&svg, `<title>%s</title>`, html.EscapeString(title))
	hatchID := "hatch-" + id
	fmt.Fprintf(&svg, `<defs>`+
		`<pattern id="%[1]s" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">`+
		`<rect class="hatch-bg" width="6" height="6"/><line class="hatch-line" x1="0" y1="0" x2="0" y2="6"/></pattern>`+
		`<pattern id="%[1]s-hover" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">`+
		`<rect class="hatch-bg-hover" width="6" height="6"/><line class="hatch-line-hover" x1="0" y1="0" x2="0" y2="6"/></pattern>`+
		`</defs>`,
		html.EscapeString(hatchID))
	for i := 0; i <= gridLines; i++ {
		gridValue := yMax * float64(i) / gridLines
		gridY := top + plotH - plotH*float64(i)/gridLines
		fmt.Fprintf(&svg, `<line class="grid" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>`, left, gridY, width-right, gridY)
		fmt.Fprintf(&svg, `<text class="axis" x="%.1f" y="%.1f" text-anchor="end">%s</text>`, left-6, gridY+4, html.EscapeString(tick(gridValue)))
	}
	count := len(points)
	if count == 0 {
		svg.WriteString(`</svg>`)
		return template.HTML(svg.String())
	}
	slot := plotW / float64(count)
	barW := math.Max(slot*barFrac, minBarGap)
	labelEvery := int(math.Ceil(float64(count) / maxLabels))
	for i, point := range points {
		barX := left + slot*float64(i) + (slot-barW)/2
		barH := 0.0
		if yMax > 0 {
			barH = plotH * point.Value / yMax
		}
		if point.Value > 0 && barH < 1.5 {
			barH = 1.5
		}
		barY := top + plotH - barH
		attrs := `class="bar"`
		switch {
		case point.Incomplete:
			barH = math.Max(barH, minIncompleteHeight)
			barY = top + plotH - barH
			attrs = fmt.Sprintf(`class="bar-incomplete" fill="url(#%[1]s)" data-hover-fill="url(#%[1]s-hover)"`, html.EscapeString(hatchID))
		case point.Value == 0:
			attrs = `class="bar empty"`
			barH, barY = 1, top+plotH-1
		}
		fmt.Fprintf(&svg, `<path %s d="%s" data-tip="%s: %s"></path>`,
			attrs, barPath(barX, barY, barW, barH), html.EscapeString(point.Hover), html.EscapeString(point.Text))
		if i%labelEvery == 0 {
			label := point.Label
			if len(label) == 10 {
				label = label[5:]
			}
			fmt.Fprintf(&svg, `<text class="axis" x="%.1f" y="%.1f" text-anchor="middle">%s</text>`,
				barX+barW/2, height-bottom+18, html.EscapeString(label))
		}
	}
	svg.WriteString(`</svg>`)
	return template.HTML(svg.String())
}
