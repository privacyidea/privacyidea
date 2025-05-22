import {
  computed,
  effect,
  Injectable,
  linkedSignal,
  signal,
  WritableSignal,
} from '@angular/core';
import {
  HttpClient,
  HttpErrorResponse,
  HttpParams,
  httpResource,
} from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { LocalService } from '../local/local.service';
import { NotificationService } from '../notification/notification.service';
import { TableUtilsService } from '../table-utils/table-utils.service';
import { TokenService } from '../token/token.service';
import {
  catchError,
  forkJoin,
  Observable,
  of,
  Subject,
  switchMap,
  takeUntil,
  takeWhile,
  throwError,
  timer,
} from 'rxjs';
import { Sort } from '@angular/material/sort';
import { ContainerTypeOption } from '../../components/token/container-create/container-create.component';
import { ContentService } from '../content/content.service';
import { PiResponse } from '../../app.component';

const apiFilter = ['container_serial', 'type', 'user'];
const advancedApiFilter = ['token_serial'];

export interface ContainerResponse {
  result: {
    value: {
      containers: [
        {
          states: string[];
        },
      ];
      count: number;
    };
  };
}

export interface ContainerDetail {
  containers: Array<ContainerDetailData>;
}

export interface ContainerDetailData {
  type: string;
  tokens: Array<ContainerDetailToken>;
  states: string[];
  description: string;
  select: string;
  serial: string;
  users: ContainerDetailUser[];
  user_realm: string;
  realms: string[];
}

export interface ContainerDetailToken {
  active: boolean;
  container_serial: string;
  count: number;
  count_window: number;
  description: string;
  failcount: number;
  id: number;
  info: any;
  revoked: boolean;
  serial: string;
}

export interface ContainerDetailUser {
  user_realm: string;
  user_name: string;
  user_resolver: string;
  user_id: string;
}

export type ContainerTypesMap = Map<ContainerTypeOption, ContainerTypeMapValue>;
export interface ContainerTypeMapValue {
  description: string;
  token_types: string[];
}

export interface ContainerType {
  containerType: ContainerTypeOption;
  description: string;
  token_types: string[];
}

@Injectable({
  providedIn: 'root',
})
export class ContainerService {
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  stopPolling$ = new Subject<void>();
  containerBaseUrl = environment.proxyUrl + '/container/';
  eventPageSize = 10;
  states = signal<string[]>([]);
  selectedContent = this.contentService.selectedContent;
  containerSerial = this.contentService.containerSerial;
  selectedContainer: WritableSignal<string> = linkedSignal({
    source: this.selectedContent,
    computation: (selectedContent, previous) =>
      selectedContent !== 'token_enrollment' ? '' : (previous?.value ?? ''),
  });

  sort = signal<Sort>({ active: 'serial', direction: 'asc' });

  filterValue: WritableSignal<string> = linkedSignal({
    source: this.selectedContent,
    computation: () => '',
  });
  filterParams = computed<Record<string, string>>(() => {
    const { filterPairs } = this.tableUtilsService.parseFilterString(
      this.filterValue(),
      [...this.apiFilter, ...this.advancedApiFilter],
    );
    return filterPairs.reduce(
      (acc, { key, value }) => {
        if (
          key === 'user' ||
          key === 'type' ||
          key === 'container_serial' ||
          key === 'token_serial'
        ) {
          acc[key] = `${value}`;
        } else {
          acc[key] = `*${value}*`;
        }
        return acc;
      },
      {} as Record<string, string>,
    );
  });
  pageSize = linkedSignal({
    source: this.filterValue,
    computation: (): any => {
      if (![5, 10, 15].includes(this.eventPageSize)) {
        return 10;
      }
      return this.eventPageSize;
    },
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize(),
      selectedContent: this.selectedContent(),
    }),
    computation: () => 0,
  });
  loadAllContainers = computed(() => {
    return (
      this.selectedContent() === 'token_details' ||
      this.selectedContent() === 'token_enrollment'
    );
  });
  containerResource = httpResource<ContainerResponse>(() => {
    if (
      !['container_overview', 'token_detail', 'token_enrollment'].includes(
        this.selectedContent(),
      )
    ) {
      return undefined;
    }
    return {
      url: this.containerBaseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: {
        ...(!this.loadAllContainers() && {
          page: this.pageIndex() + 1,
          pagesize: this.pageSize(),
        }),
        sortby: this.sort().active,
        sortdir: this.sort().direction,
        no_token: this.loadAllContainers() ? 1 : 0,
        ...this.filterParams(),
      },
    };
  });
  containerOptions = linkedSignal({
    source: this.containerResource.value,
    computation: (containerResource) => {
      if (containerResource) {
        return containerResource.result.value.containers.map(
          (container: any) => container.serial,
        );
      }
      return [];
    },
  });
  filteredContainerOptions = computed(() => {
    const filter = (this.selectedContainer() || '').toLowerCase();
    return this.containerOptions().filter((option) =>
      option.toLowerCase().includes(filter),
    );
  });

  containerSelection: WritableSignal<any[]> = linkedSignal({
    source: () => ({
      pageIndex: this.pageIndex(),
      pageSize: this.pageSize(),
      sort: this.sort(),
      filterValue: this.filterValue(),
    }),
    computation: () => [],
  });

  containerTypesResource = httpResource<PiResponse<ContainerTypesMap>>(() => ({
    url: `${this.containerBaseUrl}types`,
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  containerTypeOptions = computed<ContainerType[]>(() => {
    const value = this.containerTypesResource.value()?.result.value;
    if (!value) {
      return [];
    }
    return Array.from(Object.entries(value)).map(([key, containerType]) => ({
      containerType: key as ContainerTypeOption,
      description: containerType?.description ?? '',
      token_types: containerType?.token_types ?? [],
    }));
  });

  selectedContainerType = linkedSignal({
    source: this.selectedContent,
    computation: () =>
      this.containerTypeOptions()[0] ?? [
        {
          key: 'generic',
          description: 'No container type data available',
          token_types: [],
        },
      ],
  });

  containerDetailResource = httpResource<PiResponse<ContainerDetail>>(() => {
    const serial = this.containerSerial();

    if (serial === '') {
      return undefined;
    }
    return {
      url: this.containerBaseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: {
        container_serial: serial,
      },
    };
  });
  containerDetail: WritableSignal<ContainerDetail> = linkedSignal({
    source: this.containerDetailResource.value,
    computation: (containerDetailResource, previous) => {
      if (containerDetailResource?.result?.value) {
        return containerDetailResource.result.value;
      }
      return (
        previous?.value ?? {
          containers: [],
        }
      );
    },
  });

  templatesResource = httpResource<any>(() => ({
    url: `${this.containerBaseUrl}templates`,
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
    private tokenService: TokenService,
    private notificationService: NotificationService,
    private contentService: ContentService,
  ) {
    effect(() => {
      if (this.containerDetailResource.error()) {
        const containerDetailError =
          this.containerDetailResource.error() as HttpErrorResponse;
        console.error(
          'Failed to get container details.',
          containerDetailError.message,
        );
        const message =
          containerDetailError.error?.result?.error?.message ||
          containerDetailError.message;
        this.notificationService.openSnackBar(
          'Failed to get container details.' + message,
        );
      }
    });
    effect(() => {
      if (this.containerResource.error()) {
        const error = this.containerResource.error() as HttpErrorResponse;
        this.notificationService.openSnackBar(error.message);
      }
    });
  }

  assignContainer(tokenSerial: string, containerSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post<
        PiResponse<boolean>
      >(`${this.containerBaseUrl}${containerSerial}/add`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to assign container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to assign container. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  unassignContainer(tokenSerial: string, containerSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post<
        PiResponse<boolean>
      >(`${this.containerBaseUrl}${containerSerial}/remove`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to unassign container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to unassign container. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setContainerRealm(containerSerial: string, value: string[]) {
    const headers = this.localService.getHeaders();
    const valueString = value ? value.join(',') : '';
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/realms`,
        { realms: valueString },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to set container realm.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set container realm. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setContainerDescription(containerSerial: string, value: any) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/description`,
        { description: value },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to set container description.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set container description. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  toggleActive(containerSerial: string, states: string[]): Observable<any> {
    const headers = this.localService.getHeaders();
    let new_states = states
      .map((state) => {
        if (state === 'active') {
          return 'disabled';
        } else if (state === 'disabled') {
          return 'active';
        } else {
          return state;
        }
      })
      .join(',');
    if (!(states.includes('active') || states.includes('disabled'))) {
      new_states = states.concat('active').join(',');
    }
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/states`,
        { states: new_states },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to toggle active.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to toggle active. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  unassignUser(containerSerial: string, username: string, userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/unassign`,
        { user: username, realm: userRealm },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to unassign user.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to unassign user. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  assignUser(args: {
    containerSerial: string;
    username: string;
    userRealm: string;
  }) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${args.containerSerial}/assign`,
        { user: args.username, realm: args.userRealm },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to assign user.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to assign user. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setContainerInfos(containerSerial: string, infos: any) {
    const headers = this.localService.getHeaders();
    const info_url = `${this.containerBaseUrl}${containerSerial}/info`;
    return Object.keys(infos).map((info) => {
      const infoValue = infos[info];
      return this.http
        .post(`${info_url}/${info}`, { value: infoValue }, { headers })
        .pipe(
          catchError((error) => {
            console.error('Failed to save container infos.', error);
            const message = error.error?.result?.error?.message || '';
            this.notificationService.openSnackBar(
              'Failed to save container infos. ' + message,
            );
            return throwError(() => error);
          }),
        );
    });
  }

  deleteInfo(containerSerial: string, key: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .delete(`${this.containerBaseUrl}${containerSerial}/info/delete/${key}`, {
        headers,
      })
      .pipe(
        catchError((error) => {
          console.error('Failed to delete info.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to delete info. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  addTokenToContainer(containerSerial: string, tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/add`,
        { serial: tokenSerial },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to add token to container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to add token to container. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/remove`,
        { serial: tokenSerial },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to remove token from container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to remove token from container. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  toggleAll(
    containerSerial: string,
    action: 'activate' | 'deactivate',
  ): Observable<any> {
    const data = this.containerDetail();

    if (!data || !Array.isArray(data.containers[0].tokens)) {
      this.notificationService.openSnackBar(
        'No valid tokens array found in data.',
      );
      return of(null);
    }

    const tokensForAction =
      action === 'activate'
        ? data.containers[0].tokens.filter((token: any) => !token.active)
        : data.containers[0].tokens.filter((token: any) => token.active);

    if (tokensForAction.length === 0) {
      this.notificationService.openSnackBar('No tokens for action.');
      return of(null);
    }
    return forkJoin(
      tokensForAction.map(
        (token: { serial: string; active: boolean; revoked: boolean }) => {
          return !token.revoked
            ? this.tokenService.toggleActive(token.serial, token.active)
            : of(null);
        },
      ),
    ).pipe(
      catchError((error) => {
        console.error('Failed to toggle all.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to toggle all. ' + message,
        );
        return throwError(() => error);
      }),
    );
  }

  removeAll(containerSerial: string) {
    const data = this.containerDetail();

    if (!data || !Array.isArray(data.containers[0].tokens)) {
      console.error('No valid tokens array found in data.', data);
      this.notificationService.openSnackBar(
        'No valid tokens array found in data.',
      );
      return of(null);
    }

    const tokensForAction = data.containers[0].tokens.map(
      (token: any) => token.serial,
    );

    if (tokensForAction.length === 0) {
      console.error('No tokens to remove. Returning []');
      this.notificationService.openSnackBar('No tokens to remove.');
      return of(null);
    }

    const headers = this.localService.getHeaders();

    return this.http
      .post<
        PiResponse<boolean>
      >(`${this.containerBaseUrl}${containerSerial}/removeall`, { serial: tokensForAction.join(',') }, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to remove all.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to remove all. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  deleteContainer(containerSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .delete(`${this.containerBaseUrl}${containerSerial}`, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to delete container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to delete container. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  deleteAllTokens(param: { containerSerial: string; serialList: string }) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${param.containerSerial}/removeall`,
        { serial: param.serialList },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to delete all tokens.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to delete all tokens. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  createContainer(param: {
    container_type: string;
    description?: string;
    user_realm?: string;
    template?: string;
    user?: string;
    realm?: string;
    options?: any;
  }) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}init`,
        {
          type: param.container_type,
          description: param.description,
          user: param.user,
          realm: param.user_realm,
          template: param.template,
          options: param.options,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to create container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to create container. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  registerContainer(params: {
    container_serial: string;
    passphrase_prompt: string;
    passphrase_response: string;
  }) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}register/initialize`,
        {
          container_serial: params.container_serial,
          passphrase_ad: false,
          passphrase_prompt: params.passphrase_prompt,
          passphrase_response: params.passphrase_response,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to register container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to register container. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  stopPolling() {
    this.stopPolling$.next();
  }

  getContainerDetails(containerSerial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams().set('container_serial', containerSerial);
    return this.http.get(this.containerBaseUrl, { headers, params });
  }

  pollContainerRolloutState(
    containerSerial: string,
    startTime: number,
  ): Observable<any> {
    this.containerSerial.set(containerSerial);
    return timer(startTime, 2000).pipe(
      takeUntil(this.stopPolling$),
      switchMap(() => this.getContainerDetails(this.containerSerial())),
      takeWhile(
        (response: any) =>
          response.result.value.containers[0].info.registration_state ===
          'client_wait',
        true,
      ),
      catchError((error) => {
        console.error('Failed to poll container state.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to poll container state. ' + message,
        );
        return throwError(() => error);
      }),
    );
  }
}
