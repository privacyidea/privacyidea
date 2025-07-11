import { httpResource } from '@angular/common/http';
import { Injectable, linkedSignal, WritableSignal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import { LocalService } from '../local/local.service';

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

@Injectable({
  providedIn: 'root',
})
export class ApplicationService {
  readonly applicationBaseUrl = environment.proxyUrl + '/application/';

  constructor(private localService: LocalService) {}

  applicationResource = httpResource<PiResponse<Applications>>(() => ({
    url: `${this.applicationBaseUrl}`,
    method: 'GET',
    headers: this.localService.getHeaders(),
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
              totp: { partition: { type: '' }, slot: { type: '', value: [] } },
            },
          },
          offline: {
            options: {
              hotp: { count: { type: '' }, rounds: { type: '' } },
              passkey: {},
              webauthn: {},
            },
          },
          ssh: {
            options: {
              sshkey: {
                service_id: { description: '', type: '', value: [] },
                user: { description: '', type: '' },
              },
            },
          },
        }
      );
    },
  });
}
