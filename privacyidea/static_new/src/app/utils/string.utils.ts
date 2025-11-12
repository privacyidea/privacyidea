/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

export class StringUtils {
  static replaceWithTags(template: string, tagData: Record<string, string>): string {
    let result = template;
    Object.entries(tagData).forEach(([tag, value]) => {
      const regex = new RegExp(`{{\\s*${tag}\\s*}}`, "g");
      result = result.replace(regex, value);
    });
    return result;
  };

  static validFilterValue(value: string): boolean {
    // A valid filter value is not empty and not just asterisks
    return !/^\**$/.test(value.trim());
  }
}

