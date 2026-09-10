// The user roles the authentication log records, and how each is shown. Shared by every view that displays one -
// the authentication log's filter menu and role badge, and the locked-users table, whose rows carry the same
// value - so a role cannot come out named one thing in one table and another in the next.
//
// A regular user gets no badge: they are the default and would carry one on almost every row. The badge classes
// are global (src/styles/badges.scss) rather than component-scoped, for the same reason this file exists.

export interface UserRoleBadge {
  label: string;
  tooltip: string;
  class: string;
}

export const USER_ROLE_CONFIG: readonly {
  value: string;
  filterLabel: string;
  badge?: UserRoleBadge;
}[] = [
  { value: "user", filterLabel: $localize`User` },
  {
    value: "admin-internal",
    filterLabel: $localize`Internal Admin`,
    badge: {
      label: $localize`internal admin`,
      tooltip: $localize`Local database administrator.`,
      class: "role-badge-admin-internal"
    }
  },
  {
    value: "admin-external",
    filterLabel: $localize`External Admin`,
    badge: {
      label: $localize`external admin`,
      tooltip: $localize`Administrator from an admin realm.`,
      class: "role-badge-admin-external"
    }
  }
];

const USER_ROLE_BADGES: Record<string, UserRoleBadge> = Object.fromEntries(
  USER_ROLE_CONFIG.filter((role) => role.badge).map((role) => [role.value, role.badge!])
);

// The value of user_role a local database admin carries, in the log and on their lock row alike.
export const ADMIN_INTERNAL_ROLE = "admin-internal";

export function userRoleBadge(value: string | null | undefined): UserRoleBadge | null {
  return (value && USER_ROLE_BADGES[value]) || null;
}
