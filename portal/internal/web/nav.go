package web

// TabSpec defines one top-level portal navigation tab. Future portal modules
// (for example Tasks, Budgets, or Quotas) register an entry here so header
// links and date-range query propagation stay declarative.
type TabSpec struct {
	ID         string
	Label      string
	Path       string
	CarryRange bool
}

// DefaultTabs lists the six v1 portal tabs in display order.
var DefaultTabs = []TabSpec{
	{ID: "overview", Label: "Overview", Path: "/", CarryRange: true},
	{ID: "models", Label: "Models", Path: "/models", CarryRange: true},
	{ID: "errors", Label: "Errors", Path: "/errors", CarryRange: true},
	{ID: "report", Label: "Report", Path: "/report", CarryRange: true},
	{ID: "connect", Label: "Connect", Path: "/connect", CarryRange: true},
	{ID: "keys", Label: "Account", Path: "/keys", CarryRange: true},
}

type navLink struct {
	Label   string
	Href    string
	Current bool
}

func buildNav(currentPath, rangeQuery string) []navLink {
	links := make([]navLink, 0, len(DefaultTabs))
	for _, tab := range DefaultTabs {
		href := tab.Path
		if tab.CarryRange && rangeQuery != "" {
			href += "?" + rangeQuery
		}
		links = append(links, navLink{
			Label:   tab.Label,
			Href:    href,
			Current: tab.Path == currentPath,
		})
	}
	return links
}
