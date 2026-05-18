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
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { effect, inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { empty } from "rxjs";

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
  private readonly notificationService = inject(NotificationService);
  readonly applicationBaseUrl = environment.proxyUrl + "/application/";

  private readonly empty: Applications = {
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
  };

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.applicationResource.error(), "applications");
    });
  }

  applicationResource = httpResource<PiResponse<Applications>>(() => ({
    url: `${this.applicationBaseUrl}`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));
  applications: WritableSignal<Applications> = linkedSignal({
    source: () => ({
      value: this.applicationResource.hasValue() ? this.applicationResource.value() : undefined,
      isLoading: this.applicationResource.isLoading(),
      error: this.applicationResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return this.empty;
      const value = source.value?.result?.value;
      if (!value) return source.isLoading ? (previous?.value ?? this.empty) : this.empty;
      return value;
    }
  });
}
