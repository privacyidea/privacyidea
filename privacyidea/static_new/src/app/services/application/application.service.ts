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
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";

export type Applications = {
  luks: ApplicationLuks;
  offline: ApplicationOffline;
  ssh: ApplicationSsh;
};

interface ApplicationLuks {
  options: {
    totp: {
      partition: { type: string };
      slot: { type: string; value: number[] };
    };
  };
}

interface ApplicationOffline {
  options: {
    hotp: {
      count: { type: string };
      rounds: { type: string };
    };
    passkey: {};
    webauthn: {};
  };
}

interface ApplicationSsh {
  options: {
    sshkey: {
      service_id: {
        description: string;
        type: string;
        value: string[];
      };
      user: {
        description?: string;
        type: string;
      };
    };
  };
}

export interface ApplicationServiceInterface {
  applicationBaseUrl: string;
  applicationResource: HttpResourceRef<PiResponse<Applications> | undefined>;
  applications: WritableSignal<Applications>;
}

@Injectable({
  providedIn: "root"
})
export class ApplicationService implements ApplicationServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  readonly applicationBaseUrl = environment.proxyUrl + "/application/";
  applicationResource = httpResource<PiResponse<Applications>>(() => ({
    url: `${this.applicationBaseUrl}`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));
  applications: WritableSignal<Applications> = linkedSignal({
    source: this.applicationResource.value,
    computation: (source, previous) => {
      if (source?.result?.value) {
        return source.result.value;
      }
      return (
        previous?.value ?? {
          luks: {
            options: {
              totp: { partition: { type: "" }, slot: { type: "", value: [] } }
            }
          },
          offline: {
            options: {
              hotp: { count: { type: "" }, rounds: { type: "" } },
              passkey: {},
              webauthn: {}
            }
          },
          ssh: {
            options: {
              sshkey: {
                service_id: { description: "", type: "", value: [] },
                user: { description: "", type: "" }
              }
            }
          }
        }
      );
    }
  });
}
