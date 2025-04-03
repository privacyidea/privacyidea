import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import {
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
import { catchError, map } from 'rxjs/operators';
import { LocalService } from '../local/local.service';
import { Sort } from '@angular/material/sort';
import { TableUtilsService } from '../table-utils/table-utils.service';
import { TokenService } from '../token/token.service';
import { NotificationService } from '../notification/notification.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ContainerService {
  private stopPolling$ = new Subject<void>();
  private containerBaseUrl = environment.proxyUrl + '/container/';
  apiFilter = ['container_serial', 'type', 'user'];
  advancedApiFilter = ['token_serial'];

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
    private tokenService: TokenService,
    private notificationService: NotificationService,
  ) {}

  getContainerData(
    options: {
      page?: number;
      pageSize?: number;
      sort?: Sort;
      filterValue?: string;
      noToken?: boolean;
    } = {},
  ): Observable<any> {
    const { page, pageSize, sort, filterValue, noToken } = options;
    const headers = this.localService.getHeaders();
    let params = new HttpParams();

    if (page && pageSize) {
      params = params
        .set('page', page.toString())
        .set('pagesize', pageSize.toString());
    }
    if (sort) {
      params = params.set('sortby', sort.active).set('sortdir', sort.direction);
    }

    if (filterValue) {
      let combinedFilter = [...this.apiFilter, ...this.advancedApiFilter];
      const { filterPairs, remainingFilterText } =
        this.tableUtilsService.parseFilterString(filterValue, combinedFilter);
      filterPairs.forEach(({ key, value }) => {
        if (
          key === 'user' ||
          key === 'type' ||
          key === 'container_serial' ||
          key === 'token_serial'
        ) {
          params = params.set(key, `${value}`);
        } else {
          params = params.set(key, `*${value}*`);
        }
      });

      /* TODO global filtering is missing in api
      if (remainingFilterText) {
        params = params.set('globalfilter', `*${remainingFilterText}*`);
      }
      */
    }

    if (noToken) {
      params = params.set('no_token', 1);
    }

    return this.http.get<any>(this.containerBaseUrl, { headers, params }).pipe(
      map((response) => response),
      catchError((error) => {
        console.error('Failed to get container data.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to get container data. ' + message,
        );
        return throwError(() => error);
      }),
    );
  }

  assignContainer(tokenSerial: string, containerSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/add`,
        {
          serial: tokenSerial,
        },
        { headers },
      )
      .pipe(
        map((response) => response),
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
      .post(
        `${this.containerBaseUrl}${containerSerial}/remove`,
        {
          serial: tokenSerial,
        },
        { headers },
      )
      .pipe(
        map((response) => response),
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

  getContainerDetails(containerSerial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams().set('container_serial', containerSerial);
    return this.http.get(this.containerBaseUrl, { headers, params });
  }

  setContainerRealm(containerSerial: string, value: string[]) {
    const headers = this.localService.getHeaders();
    let valueString = value ? value.join(',') : '';
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/realms`,
        {
          realms: valueString,
        },
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
        {
          description: value,
        },
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
        {
          user: username,
          realm: userRealm,
        },
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

  assignUser(containerSerial: string, username: string, userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${containerSerial}/assign`,
        {
          user: username,
          realm: userRealm,
        },
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
      const infoKey = info;
      const infoValue = infos[infoKey];
      return this.http
        .post(`${info_url}/${infoKey}`, { value: infoValue }, { headers })
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
        {
          serial: tokenSerial,
        },
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
        {
          serial: tokenSerial,
        },
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
    return this.getContainerDetails(containerSerial).pipe(
      map((data) => {
        if (!data || !Array.isArray(data.result.value.containers[0].tokens)) {
          console.error('No valid tokens array found in data.', data);
          this.notificationService.openSnackBar(
            'No valid tokens array found in data.',
          );
          return [];
        }
        if (action === 'activate') {
          return data.result.value.containers[0].tokens.filter(
            (token: any) => !token.active,
          );
        } else {
          return data.result.value.containers[0].tokens.filter(
            (token: any) => token.active,
          );
        }
      }),

      switchMap((tokensForAction) => {
        if (tokensForAction.length === 0) {
          console.error('No tokens for action. Returning []');
          this.notificationService.openSnackBar('No tokens for action.');
          return of([]);
        }
        return forkJoin(
          tokensForAction.map(
            (token: { serial: string; active: boolean; revoked: boolean }) => {
              if (!token.revoked) {
                return this.tokenService.toggleActive(
                  token.serial,
                  token.active,
                );
              } else {
                return of(null);
              }
            },
          ),
        );
      }),

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

  removeAll(containerSerial: string): Observable<any> {
    return this.getContainerDetails(containerSerial).pipe(
      map((data) => {
        if (!data || !Array.isArray(data.result.value.containers[0].tokens)) {
          console.error('No valid tokens array found in data.', data);
          this.notificationService.openSnackBar(
            'No valid tokens array found in data.',
          );
          return [];
        }
        return data.result.value.containers[0].tokens.map(
          (token: any) => token.serial,
        );
      }),

      switchMap((tokensForAction) => {
        if (tokensForAction.length === 0) {
          console.error('No tokens to remove. Returning []');
          this.notificationService.openSnackBar('No tokens to remove.');
          return of([]);
        }
        const headers = this.localService.getHeaders();
        return this.http.post(
          `${this.containerBaseUrl}${containerSerial}/removeall`,
          {
            serial: tokensForAction.join(','),
          },
          { headers },
        );
      }),
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
      .delete(`${this.containerBaseUrl}${containerSerial}`, {
        headers,
      })
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
        {
          serial: param.serialList,
        },
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

  getTemplates() {
    const headers = this.localService.getHeaders();
    return this.http.get<any>(`${this.containerBaseUrl}templates`, {
      headers,
    });
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

  pollContainerRolloutState(
    containerSerial: string,
    startTime: number,
  ): Observable<any> {
    return timer(startTime, 2000).pipe(
      takeUntil(this.stopPolling$),
      switchMap(() => this.getContainerDetails(containerSerial)),
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
