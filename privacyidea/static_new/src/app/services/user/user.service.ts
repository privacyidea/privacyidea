import { computed, Injectable, Signal, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { catchError, map } from 'rxjs/operators';
import { NotificationService } from '../notification/notification.service';
import { distinctUntilChanged, from, switchMap, throwError } from 'rxjs';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';

@Injectable({
  providedIn: 'root',
})
export class UserService {
  private baseUrl = environment.proxyUrl + '/user/';
  selectedUserRealm = signal<string>('');
  selectedUsername = signal<string>('');
  fetchedUsernames: Signal<string[]> = toSignal(
    toObservable(this.selectedUserRealm).pipe(
      distinctUntilChanged(),
      switchMap((realm) => {
        if (!realm) {
          return from<string[]>([]);
        }
        return this.getUsers(realm).pipe(
          map((result: any) => result.value.map((user: any) => user.username)),
        );
      }),
    ),
    { initialValue: [] },
  );
  userOptions = computed(() => this.fetchedUsernames());
  filteredUserOptions = computed(() => {
    const filterValue = (this.selectedUsername() || '').toLowerCase();
    return this.userOptions().filter((option: any) =>
      option.toLowerCase().includes(filterValue),
    );
  });

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private notificationService: NotificationService,
  ) {}

  setDefaultRealm(realmService: any): void {
    realmService.getDefaultRealm().subscribe({
      next: (realm: any) => {
        this.selectedUserRealm.set(realm);
      },
    });
  }

  resetUserSelection(): void {
    this.selectedUsername.set('');
    this.selectedUserRealm.set('');
  }

  getUsers(userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .get(`${this.baseUrl}?realm=${userRealm}`, { headers })
      .pipe(
        map((response: any) => response.result),
        catchError((error) => {
          console.error('Failed to get users.', error);
          this.notificationService.openSnackBar('Failed to get users.');
          return throwError(() => error);
        }),
      );
  }
}
