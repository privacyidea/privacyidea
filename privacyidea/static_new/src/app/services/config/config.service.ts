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
import { inject, Injectable, signal } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { catchError } from "rxjs/operators";
import { of } from "rxjs";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";

export interface AppConfig {
  remote_user: string;
  force_remote_user: string;
  password_reset: boolean;
  hsm_ready: boolean;
  customization: string;
  realms: string;
  logo: string;
  show_node: string;
  external_links: boolean;
  has_job_queue: string;
  login_text: string;
  gdpr_link: string;
  translation_warning: boolean;
}

@Injectable({
  providedIn: "root"
})
export class ConfigService {
  http: HttpClient = inject(HttpClient);
  config = signal({
    remote_user: "",
    force_remote_user: "",
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
    translation_warning: false
  });

  loadConfig() {
    return this.http.get<PiResponse<Record<any, any>>>(environment.proxyUrl + "/config")
      .pipe(
        catchError((error) => {
          console.error("Failed to load config:", error);
          return of({
            id: 0,
            jsonrpc: "",
            detail: {},
            result: { status: false, value: this.config() },
            signature: "",
            time: 0,
            version: "",
            versionnumber: ""
          } as PiResponse<Record<any, any>>);
        })
      )
      .subscribe((data) => {
        this.config.set(data.result?.value as AppConfig);
      });
  }
}