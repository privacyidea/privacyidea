import {Component, effect, Input, Output, signal, WritableSignal} from '@angular/core';
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatRow,
  MatRowDef,
  MatTable,
} from '@angular/material/table';
import {MatFabButton, MatIconButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {TokenService} from '../../../services/token/token.service';
import {ContainerService} from '../../../services/container/container.service';
import {AsyncPipe, NgClass} from '@angular/common';
import {MatGridList, MatGridTile} from '@angular/material/grid-list';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatInput, MatSuffix} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatDivider} from '@angular/material/divider';
import {MatSelectModule} from '@angular/material/select';
import {forkJoin, Observable, startWith, switchMap} from 'rxjs';
import {ValidateService} from '../../../services/validate/validate.service';
import {RealmService} from '../../../services/realm/realm.service';
import {UserService} from '../../../services/user/user.service';
import {map} from 'rxjs/operators';
import {TableUtilsService} from '../../../services/table-utils/table-utils.service';
import {TokenDetailsUserComponent} from './token-details-user/token-details-user.component';
import {MatAutocomplete, MatAutocompleteTrigger} from "@angular/material/autocomplete";

export const details = [
  {key: 'tokentype', label: 'Type'},
  {key: 'active', label: 'Active'},
  {key: 'maxfail', label: 'Max Count'},
  {key: 'failcount', label: 'Fail Count'},
  {key: 'otplen', label: 'OTP Length'},
  {key: 'count_window', label: 'Count Window'},
  {key: 'sync_window', label: 'Sync Window'},
  {key: 'count', label: 'Count'},
  {key: 'description', label: 'Description'},
  {key: 'realms', label: 'Token Realms'},
  {key: 'tokengroup', label: 'Token Group'},
  {key: 'container_serial', label: 'Container Serial'},
];

export const userDetail = [
  {key: 'user_realm', label: 'User Realm'},
  {key: 'username', label: 'User'},
  {key: 'resolver', label: 'Resolver'},
  {key: 'user_id', label: 'User ID'},
];

export const infoDetail = [
  {key: 'info', label: 'Information'},
];

@Component({
  selector: 'app-token-details',
  standalone: true,
  imports: [
    MatCell,
    MatCellDef,
    MatColumnDef,
    MatFabButton,
    MatHeaderCell,
    MatIcon,
    MatListItem,
    MatRow,
    MatRowDef,
    MatTable,
    MatHeaderCellDef,
    NgClass,
    MatGridTile,
    MatGridList,
    FormsModule,
    MatInput,
    MatDivider,
    MatSuffix,
    MatFormFieldModule,
    MatSelectModule,
    ReactiveFormsModule,
    MatList,
    MatIconButton,
    TokenDetailsUserComponent,
    MatAutocomplete,
    AsyncPipe,
    MatAutocompleteTrigger,
  ],
  templateUrl: './token-details.component.html',
  styleUrl: './token-details.component.css'
})
export class TokenDetailsComponent {
  protected readonly Array = Array;
  protected readonly Object = Object;
  detailData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: boolean
  }[]>([]);
  userData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: boolean
  }[]>([]);
  infoData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: boolean
  }[]>([]);
  @Output() filteredUserOptions!: Observable<string[]>;
  filteredContainerOptions!: Observable<string[]>;
  @Output() realmOptions = signal<string[]>([]);
  containerOptions = signal<string[]>([]);
  userOptions = signal<string[]>([]);
  selectedUserRealm = signal<string>('');
  newInfo: WritableSignal<{
    key: string;
    value: string
  }> = signal({key: '', value: ''});

  constructor(private tokenService: TokenService,
              private containerService: ContainerService,
              private realmService: RealmService,
              private userService: UserService,
              private validateService: ValidateService,
              protected tableUtilsService: TableUtilsService) {
    effect(() => {
      this.showTokenDetail(this.serial()).subscribe();
    });
    effect(() => {
      if (this.selectedUserRealm()) {
        this.userService.getUsers(this.selectedUserRealm()).subscribe({
          next: (users: any) => {
            this.userOptions.set(users.result.value.map((user: any) => user.username));
          },
          error: error => {
            console.error('Failed to get users', error);
          }
        });
      }
    });

    this.filteredUserOptions = this.selectedUsername.valueChanges.pipe(
      startWith(''),
      map(value => this._filterUserOptions(value || ''))
    );

    this.filteredContainerOptions = this.selectedContainer.valueChanges.pipe(
      startWith(''),
      map(value => this._filterContainerOptions(value || ''))
    );
  }

  @Input() serial!: WritableSignal<string>
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  hide!: boolean;
  @Output() isEditingUser: WritableSignal<boolean> = signal(false);
  isEditingInfo: boolean = false;
  selectedUsername = new FormControl<string>('');
  selectedContainer = new FormControl<string>('');
  @Output() setPinValue: WritableSignal<string> = signal('');
  @Output() repeatPinValue: WritableSignal<string> = signal('');
  fristOTPValue: string = '';
  secondOTPValue: string = '';
  otpOrPinToTest: string = '';
  selectedRealms = new FormControl<string[]>([]);
  userRealm: string = '';
  maxfail: number = 0;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;

  private _filterUserOptions(value: string): string[] {
    const filterValue = value.toLowerCase();
    return this.userOptions().filter(option => option.toLowerCase().includes(filterValue));
  }

  private _filterContainerOptions(value: string): string[] {
    const filterValue = value.toLowerCase();
    return this.containerOptions().filter(option => option.toLowerCase().includes(filterValue));
  }

  isObject(value: any): boolean {
    return typeof value === 'object' && value !== null;
  }

  showTokenDetail(serial: string): Observable<void> {
    return forkJoin([
      this.tokenService.getTokenDetails(serial),
      this.realmService.getRealms(),
      this.containerService.getContainerData(1, 10) // TODO only first 10 containers
    ]).pipe(
      switchMap(([tokenDetailsResponse, realms, containers]) => {
        const tokenDetails = tokenDetailsResponse.result.value.tokens[0];
        this.active.set(tokenDetails.active);
        this.revoked.set(tokenDetails.revoked);
        this.maxfail = tokenDetails.maxfail;
        this.selectedContainer.setValue(tokenDetails.container_serial);
        this.detailData.set(details.map(detail => ({
          keyMap: detail,
          value: tokenDetails[detail.key],
          isEditing: false
        })).filter(detail => detail.value !== undefined));

        this.userData.set(userDetail.map(detail => ({
          keyMap: detail,
          value: tokenDetails[detail.key],
          isEditing: false
        })).filter(detail => detail.value !== undefined));

        this.infoData.set(infoDetail.map(detail => ({
          keyMap: detail,
          value: tokenDetails[detail.key],
          isEditing: false
        })).filter(detail => detail.value !== undefined));

        this.realmOptions.set(Object.keys(realms.result.value));
        this.selectedRealms.setValue(tokenDetails.realms);
        this.userRealm = this.userData().find(
          detail => detail.keyMap.key === 'user_realm')?.value;
        this.containerOptions.set(Object.values(containers.result.value.containers as {
          serial: string
        }[]).map(container => container.serial));

        return new Observable<void>(observer => {
          observer.next();
          observer.complete();
        });
      })
    );
  }

  resetFailCount(): void {
    this.tokenService.resetFailCount(this.serial()).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: error => {
        console.error('Failed to reset fail counter', error);
      }
    });
  }

  toggleEditMode(element: any, type: string = '', action: string = ''): void {
    switch (type) {
      case 'container_serial':
        element.isEditing = !element.isEditing;
        if (action === 'save') {
          this.assignContainer();
        } else if (action === 'cancel') {
          this.selectedContainer.reset();
        }
        break;
      case 'realms':
        element.isEditing = !element.isEditing;
        if (action === 'save') {
          this.saveRealms();
        } else if (action === 'cancel') {
          this.selectedRealms.setValue(this.detailData().find(
            detail => detail.keyMap.key === 'realms')?.value);
        }
        break;
      case 'info':
        this.isEditingInfo = !this.isEditingInfo;
        if (action === 'save') {
          this.saveInfo(element.value);
          this.newInfo.set({key: '', value: ''});
        } else if (action === 'cancel') {
          this.newInfo.set({key: '', value: ''});
        }
        break;
      default:
        element.isEditing = !element.isEditing;
        if (action === 'save') {
          this.saveDetail(element.keyMap.key, element.value);
        } else if (action === 'cancel') {
          this.showTokenDetail(this.serial()).subscribe();
        }
        break;
    }
  }

  @Output()
  isAnyEditing(): boolean {
    if (this.detailData) {
      return this.detailData().some((element) => element.isEditing)
        || this.isEditingUser() || this.isEditingInfo;
    }
    return false;
  }

  saveDetail(key: string, value: string): void {
    this.tokenService.setTokenDetail(this.serial(), key, value).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      next: () => {
        this.showTokenDetail(this.serial());
      },
      error: error => {
        console.error('Failed to save token detail', error);
      }
    });
  }

  saveInfo(infos: any): void {
    if (this.newInfo().key.trim() !== '' && this.newInfo().value.trim() !== '') {
      infos[this.newInfo().key] = this.newInfo().value;
    }
    this.tokenService.setTokenInfos(this.serial(), infos).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      next: () => {
        this.showTokenDetail(this.serial());
      },
      error: error => {
        console.error('Failed to save token infos', error);
      }
    });
  }

  deleteInfo(key: string): void {
    this.tokenService.deleteInfo(this.serial(), key).pipe(
      switchMap(() => this.showTokenDetail(this.serial())),
      switchMap(() => {
        const info = this.detailData()
          .find(detail => detail.keyMap.key === 'info');
        if (info) {
          this.isEditingInfo = true;
        }
        return new Observable<void>(observer => {
          observer.next();
          observer.complete();
        });
      })
    ).subscribe({
      error: error => {
        console.error('Failed to delete info', error);
      }
    });
  }

  assignContainer() {
    this.containerService.assignContainer(this.serial(), this.selectedContainer.value).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: error => {
        console.error('Failed to assign container', error);
      }
    });
  }

  unassignContainer() {
    this.containerService.unassignContainer(this.serial(), this.selectedContainer.value).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: error => {
        console.error('Failed to unassign container', error);
      }
    });
  }

  resyncOTPToken() {
    this.tokenService.resyncOTPToken(this.serial(), this.fristOTPValue, this.secondOTPValue).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: error => {
        console.error('Failed to resync OTP token', error);
      }
    });
  }

  testToken() {
    this.validateService.testToken(this.serial(), this.otpOrPinToTest).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: (error: any) => {
        console.error('Failed to test token', error);
      }
    });
  }

  verifyOTPValue() {
    this.validateService.testToken(this.serial(), this.otpOrPinToTest, "1").pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: (error: any) => {
        console.error('Failed to verify OTP value', error);
      }
    });
  }

  private saveRealms() {
    this.tokenService.setTokenRealm(this.serial(), this.selectedRealms.value).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      next: () => {
        this.showTokenDetail(this.serial());
      },
      error: error => {
        console.error('Failed to save token realms', error);
      }
    });
  }
}
