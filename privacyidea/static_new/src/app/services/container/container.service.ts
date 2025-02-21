import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { forkJoin, Observable, of, switchMap, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { LocalService } from '../local/local.service';
import { Sort } from '@angular/material/sort';
import { TableUtilsService } from '../table-utils/table-utils.service';
import { TokenService } from '../token/token.service';
import { NotificationService } from '../notification/notification.service';

@Injectable({
  providedIn: 'root',
})
export class ContainerService {
  apiFilter = ['container_serial', 'type', 'user'];
  advancedApiFilter = ['token_serial'];
  private containerBaseUrl = '/container/';

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
    private tokenService: TokenService,
    private notificationService: NotificationService,
  ) {}

  getContainerData(
    page?: number,
    pageSize?: number,
    sort?: Sort,
    filterValue?: string,
  ): Observable<any> {
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
      const { filterPairs, remainingFilterText } =
        this.tableUtilsService.parseFilterString(filterValue, this.apiFilter);

      filterPairs.forEach(({ label, value }) => {
        if (
          label === 'user' ||
          label === 'generic' ||
          label === 'container_serial' ||
          label === 'token_serial'
        ) {
          params = params.set(label, `${value}`);
        } else {
          params = params.set(label, `*${value}*`);
        }
      });

      /* TODO global filtering is missing in api
      if (remainingFilterText) {
        params = params.set('globalfilter', `*${remainingFilterText}*`);
      }
      */
    }

    return this.http.get<any>(this.containerBaseUrl, { headers, params }).pipe(
      map((response) => response),
      catchError((error) => {
        console.error('Failed to get container data.', error);
        this.notificationService.openSnackBar('Failed to get container data.');
        return throwError(error);
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
          this.notificationService.openSnackBar('Failed to assign container.');
          return throwError(error);
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
          this.notificationService.openSnackBar(
            'Failed to unassign container.',
          );
          return throwError(error);
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
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/realms`,
      {
        realms: valueString,
      },
      { headers },
    );
  }

  setContainerDescription(containerSerial: string, value: any) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/description`,
      {
        description: value,
      },
      { headers },
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
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/states`,
      { states: new_states },
      { headers },
    );
  }

  unassignUser(containerSerial: string, username: string, userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/unassign`,
      {
        user: username,
        realm: userRealm,
      },
      { headers },
    );
  }

  assignUser(containerSerial: string, username: string, userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/assign`,
      {
        user: username,
        realm: userRealm,
      },
      { headers },
    );
  }

  setContainerInfos(containerSerial: string, infos: any) {
    const headers = this.localService.getHeaders();
    const info_url = `${this.containerBaseUrl}${containerSerial}/info`;
    return Object.keys(infos).map((info) => {
      const infoKey = info;
      const infoValue = infos[infoKey];
      return this.http.post(
        `${info_url}/${infoKey}`,
        { value: infoValue },
        { headers },
      );
    });
  }

  deleteInfo(containerSerial: string, key: string) {
    const headers = this.localService.getHeaders();
    return this.http.delete(
      `${this.containerBaseUrl}${containerSerial}/info/delete/${key}`,
      { headers },
    );
  }

  addTokenToContainer(containerSerial: string, tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/add`,
      {
        serial: tokenSerial,
      },
      { headers },
    );
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/remove`,
      {
        serial: tokenSerial,
      },
      { headers },
    );
  }

  toggleAll(containerSerial: string, action: string): Observable<any> {
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
        } else if (action === 'deactivate') {
          return data.result.value.containers[0].tokens.filter(
            (token: any) => token.active,
          );
        } else {
          return data.result.value.containers[0].tokens.map(
            (token: any) => token.serial,
          );
        }
      }),

      switchMap((tokensForAction) => {
        if (tokensForAction.length === 0) {
          console.error('No tokens for action. Returning []');
          this.notificationService.openSnackBar('No tokens for action.');
          return of([]);
        }
        if (action === 'activate' || action === 'deactivate') {
          return forkJoin(
            tokensForAction.map(
              (token: {
                serial: string;
                active: boolean;
                revoked: boolean;
              }) => {
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
        } else if (action === 'remove') {
          const headers = this.localService.getHeaders();
          return this.http.post(
            `${this.containerBaseUrl}${containerSerial}/removeall`,
            {
              serial: tokensForAction.join(','),
            },
            { headers },
          );
        }
        throw new Error(`Unsupported action: ${action}`);
      }),
    );
  }

  deleteContainer(containerSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http.delete(`${this.containerBaseUrl}${containerSerial}`, {
      headers,
    });
  }

  deleteAllTokens(containerSerial: string, serial_list: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.containerBaseUrl}${containerSerial}/removeall`,
      {
        serial: serial_list,
      },
      { headers },
    );
  }
}
