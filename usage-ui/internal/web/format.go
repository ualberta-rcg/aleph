package web

import (
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

func formatInt(n int64) string {
	digits := strconv.FormatInt(n, 10)
	negative := strings.HasPrefix(digits, "-")
	if negative {
		digits = digits[1:]
	}
	var out strings.Builder
	for i, digit := range digits {
		if i > 0 && (len(digits)-i)%3 == 0 {
			out.WriteByte(',')
		}
		out.WriteRune(digit)
	}
	if negative {
		return "-" + out.String()
	}
	return out.String()
}

// formatGPUHours shows a GPU-seconds estimate in hours, with enough decimals
// that light use does not round to zero.
func formatGPUHours(seconds float64) string {
	hours := seconds / 3600
	switch {
	case hours <= 0:
		return "0"
	case hours < 0.001:
		return "<0.001"
	case hours < 1:
		return strconv.FormatFloat(hours, 'f', 3, 64)
	case hours < 10:
		return strconv.FormatFloat(hours, 'f', 2, 64)
	case hours < 100:
		return strconv.FormatFloat(hours, 'f', 1, 64)
	default:
		return formatInt(int64(math.Round(hours)))
	}
}

// trimZero drops a trailing ".0", so 500.0k reads 500k.
func trimZero(text string) string { return strings.TrimSuffix(text, ".0") }

// formatCompact is used for chart axis labels.
func formatCompact(value float64) string {
	switch {
	case value >= 1e9:
		return trimZero(strconv.FormatFloat(value/1e9, 'f', 1, 64)) + "B"
	case value >= 1e6:
		return trimZero(strconv.FormatFloat(value/1e6, 'f', 1, 64)) + "M"
	case value >= 1e3:
		return trimZero(strconv.FormatFloat(value/1e3, 'f', 1, 64)) + "k"
	case value >= 10 || value == 0:
		return strconv.FormatFloat(value, 'f', 0, 64)
	case value >= 1:
		return strconv.FormatFloat(value, 'f', 1, 64)
	default:
		// Small GPU-hour ticks such as 0.005 or 0.015.
		return strconv.FormatFloat(value, 'g', 2, 64)
	}
}

// formatSpeed shows output tokens per second, or a dash when unknown.
func formatSpeed(tokensPerSecond float64) string {
	switch {
	case tokensPerSecond <= 0:
		return "—"
	case tokensPerSecond >= 100:
		return formatInt(int64(math.Round(tokensPerSecond)))
	default:
		return strconv.FormatFloat(tokensPerSecond, 'f', 1, 64)
	}
}

// formatTokenWords writes large token counts in words for the report
// sentence: "3.1 million", "1.2 billion", or "84,210".
func formatTokenWords(tokens int64) string {
	scaled := func(value float64, unit string) string {
		text := strconv.FormatFloat(value, 'f', 1, 64)
		return strings.TrimSuffix(text, ".0") + " " + unit
	}
	switch {
	case tokens >= 1e9:
		return scaled(float64(tokens)/1e9, "billion")
	case tokens >= 1e6:
		return scaled(float64(tokens)/1e6, "million")
	default:
		return formatInt(tokens)
	}
}

func formatTS(t time.Time) string {
	if t.IsZero() {
		return "unknown"
	}
	return t.UTC().Format("2006-01-02 15:04 UTC")
}

// formatLongDate writes a day as "1 November 2026".
func formatLongDate(day time.Time) string { return day.UTC().Format("2 January 2006") }

// share returns a percentage of part in whole, for table bars.
func share(part, whole int64) int {
	if whole <= 0 {
		return 0
	}
	return int(part * 100 / whole)
}

// changeText describes a value against the same-length period before it:
// "+18% vs the previous 14 days". It returns "" when both are zero.
func changeText(current, previous float64, days int) string {
	period := fmt.Sprintf("the previous %d days", days)
	if days == 1 {
		period = "the previous day"
	}
	if previous <= 0 {
		if current <= 0 {
			return ""
		}
		return "none in " + period
	}
	percent := math.Round((current - previous) / previous * 100)
	switch {
	case percent == 0:
		return "same as " + period
	case percent > 0:
		return fmt.Sprintf("+%s%% vs %s", formatInt(int64(percent)), period)
	default:
		return fmt.Sprintf("−%s%% vs %s", formatInt(int64(-percent)), period)
	}
}

// countOf writes a count with its noun in the right number: "1 error",
// "2,340 errors". Templates use it as the "count" function.
func countOf(count int64, singular, pluralForm string) string {
	if count == 1 {
		return "1 " + singular
	}
	return formatInt(count) + " " + pluralForm
}

// nearLimitPercent is ledger.NearLimitFraction in whole percent, so the page
// text always names the threshold the counts actually use.
func nearLimitPercent() int { return int(math.Round(ledger.NearLimitFraction * 100)) }
