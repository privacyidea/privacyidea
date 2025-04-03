import { Injectable, signal } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { LocalService } from '../local/local.service';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { catchError, map } from 'rxjs/operators';
import { NotificationService } from '../notification/notification.service';

@Injectable({
  providedIn: 'root',
})
export class RealmService {
  realmOptions = signal<string[]>([]);
  selectedRealms = signal<string[]>([]);

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private notificationService: NotificationService,
  ) {}

  resetRealmSelection(): void {
    this.selectedRealms.set([]);
  }

  getRealms(): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.get(environment.proxyUrl + '/realm/', { headers }).pipe(
      catchError((error) => {
        console.error('Failed to get realms.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to get realms. ' + message,
        );
        return throwError(() => error);
      }),
    );
  }

  getDefaultRealm() {
    const headers = this.localService.getHeaders();
    return this.http
      .get(environment.proxyUrl + '/defaultrealm', { headers })
      .pipe(
        map((response: any) => Object.keys(response.result.value)[0]),
        catchError((error) => {
          console.error('Failed to get default realm.', error);
          return throwError(() => error);
        }),
      );
  }
}
