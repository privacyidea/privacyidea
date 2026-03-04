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
import { ConfigServiceInterface } from "../../app/services/config/config.service";
import { signal } from "@angular/core";

export class MockConfigService implements ConfigServiceInterface {
  config = signal({
    remote_user: "",
    force_remote_user: false,
    password_reset: false,
    hsm_ready: false,
    customization: "",
    realms: "",
    logo: "",
    show_node: "",
    external_links: false,
    has_job_queue: "false",
    login_text: "",
    gdpr_link: "",
    translation_warning: false,
    passkey_login: "show"
  });

  loadConfig = jest.fn().mockImplementation(() => {});
}