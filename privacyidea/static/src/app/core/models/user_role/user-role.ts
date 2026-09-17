/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

// Which kind of principal a row is about, as the backend spells it (AuthLogUserRole). API vocabulary rather than
// presentation: it is the value of the authentication log's user_role column and filter, and of the user_role field
// a lock row and a lock-reset request carry. It therefore lives here rather than beside the badge table that
// displays it (components/logs/user-roles.ts), so that the services speaking this API do not have to reach up into
// the components layer to name it.
export type UserRole = "user" | "admin-internal" | "admin-external";

// The role of a local database admin, who is identified by login name alone: they have no resolver, uid or realm,
// so this is what separates their rows from those of an ordinary user of the same name.
export const ADMIN_INTERNAL_ROLE = "admin-internal" satisfies UserRole;
