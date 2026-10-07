// Every admin page the suite visits, relative to the app's base URL. Detail pages that need an existing
// record are not listed; the forms below ("new"/"create") cover their templates.

export interface PageRoute {
  name: string;
  path: string;
}

// Pages built around a filterable, paginated table (.table-scroll-region + .filter-paginator-container).
export const TABLE_PAGES: PageRoute[] = [
  { name: "tokens", path: "tokens" },
  { name: "challenges", path: "tokens/challenges" },
  { name: "containers", path: "containers" },
  { name: "container templates", path: "containers/templates" },
  { name: "users", path: "users" },
  { name: "realms", path: "users/realms" },
  { name: "resolvers", path: "users/resolvers" },
  { name: "policies", path: "policies" },
  { name: "conditional access", path: "policies/conditional-access" },
  { name: "api clients", path: "policies/api-clients" },
  { name: "events", path: "events" },
  { name: "machines", path: "configuration/machines" },
  { name: "machine resolvers", path: "configuration/machine_resolver" },
  { name: "periodic tasks", path: "configuration/periodic-tasks" },
  { name: "audit", path: "logs/audit" },
  { name: "authentication log", path: "logs/authentication-log" },
  { name: "clients", path: "logs/clients" },
  { name: "locked users", path: "logs/locked-users" },
  { name: "blocklist", path: "logs/blocklist" },
  { name: "smtp servers", path: "external-services/smtp" },
  { name: "radius servers", path: "external-services/radius" },
  { name: "sms gateways", path: "external-services/sms" },
  { name: "privacyidea servers", path: "external-services/privacyidea" },
  { name: "ca connectors", path: "external-services/ca-connectors" },
  { name: "tokengroups", path: "external-services/tokengroups" },
  { name: "service ids", path: "external-services/service-ids" }
];

// Create/edit forms and other non-table pages.
export const OTHER_PAGES: PageRoute[] = [
  { name: "dashboard", path: "dashboard" },
  { name: "token enrollment", path: "tokens/enrollment" },
  { name: "token applications", path: "tokens/applications" },
  { name: "token get serial", path: "tokens/get-serial" },
  { name: "token import", path: "tokens/import" },
  { name: "container create", path: "containers/create" },
  { name: "container template create", path: "containers/templates/create" },
  { name: "user create", path: "users/new" },
  { name: "resolver create", path: "users/resolvers/new" },
  { name: "policy create", path: "policies/new" },
  { name: "conditional access create", path: "policies/conditional-access/new" },
  { name: "api client create", path: "policies/api-clients/new" },
  { name: "event create", path: "events/new" },
  { name: "machine resolver create", path: "configuration/machine_resolver/new" },
  { name: "periodic task create", path: "configuration/periodic-tasks/new" },
  { name: "subscription", path: "configuration/subscription" },
  { name: "system config", path: "configuration/system" },
  { name: "ui settings", path: "configuration/ui-settings" },
  { name: "token type config", path: "configuration/tokens" },
  { name: "news", path: "news" },
  { name: "smtp create", path: "external-services/smtp/new" },
  { name: "radius create", path: "external-services/radius/new" },
  { name: "sms create", path: "external-services/sms/new" },
  { name: "privacyidea server create", path: "external-services/privacyidea/new" },
  { name: "ca connector create", path: "external-services/ca-connectors/new" },
  { name: "tokengroup create", path: "external-services/tokengroups/new" },
  { name: "service id create", path: "external-services/service-ids/new" }
];

export const ALL_PAGES: PageRoute[] = [...TABLE_PAGES, ...OTHER_PAGES];

// Browser zoom as Chrome applies it on a 1920x1080 screen: the CSS viewport shrinks by the zoom factor.
export const ZOOMS = [1, 1.25, 1.5, 2] as const;
export const SCREEN = { width: 1920, height: 1080 } as const;
