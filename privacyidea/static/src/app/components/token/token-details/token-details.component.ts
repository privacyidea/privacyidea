import {Component, effect, Input, signal, WritableSignal} from '@angular/core';
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
import {MatFabButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {TokenService} from '../../../services/token/token.service';
import {ContainerService} from '../../../services/container/container.service';
import {NgClass} from '@angular/common';
import {MatGridList, MatGridTile} from '@angular/material/grid-list';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatInput, MatSuffix} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatDivider} from '@angular/material/divider';
import {MatSelectModule} from '@angular/material/select';
import {forkJoin, Observable, switchMap} from 'rxjs';

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
  {key: 'realms', label: 'Token Realm'},
  {key: 'tokengroup', label: 'Token Group'},
  {key: 'container_serial', label: 'Container Serial'},
];

export const userDetail = [
  {key: 'username', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
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
    MatList,
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
  realmOptions = signal<string[]>(['']);
  containerOptions = signal<string[]>(['']);
  infos = signal<string[]>([]);
  newInfo: WritableSignal<string> = signal('');

  constructor(private tokenService: TokenService,
              private containerService: ContainerService) {
    effect(() => {
      this.showTokenDetail(this.serial()).subscribe();
    });
  }

  @Input() serial!: WritableSignal<string>
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  hide!: boolean;
  isEditingUser: boolean = false;
  username: string = '';
  userRealm: string = '';
  setPinValue: string = '';
  repeatPinValue: string = '';
  selectedContainer: string = '';
  fristOTPValue: string = '';
  secondOTPValue: string = '';
  otpOrPinToTest: string = '';

  isObject(value: any): boolean {
    return typeof value === 'object' && value !== null;
  }

  parseObjectToList(value: any): string[] {
    return Object.entries(value).map(([key, val]) => `${key}: ${val}`);
  }

  showTokenDetail(serial: string): Observable<void> {
    return forkJoin([
      this.tokenService.getTokenDetails(serial),
      this.tokenService.getRealms(),
      this.containerService.getContainerData(1, 10)
    ]).pipe(
      switchMap(([tokenDetailsResponse, realms, containers]) => {
        const tokenDetails = tokenDetailsResponse.result.value.tokens[0];
        this.active.set(tokenDetails.active);
        this.revoked.set(tokenDetails.revoked);
        this.selectedContainer = tokenDetails.container_serial;
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
        this.containerOptions.set(Object.values(containers.result.value.containers as {
          serial: string
        }[]).map(container => container.serial));
        this.containerOptions().push('');

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

  toggleEditMode(element: any, action: string = ''): void {
    if (action === 'cancel') {
      element.isEditing = false;
    } else {
      element.isEditing = !element.isEditing;
      if (element.isEditing && element.keyMap.key === 'info') {
        this.infos.set(this.parseObjectToList(element.value));
      } else if (!element.isEditing) {
        if (this.newInfo() !== '') {
          this.infos().push(this.newInfo());
        }
        if (element.keyMap.key === 'container_serial') {
          this.assignContainer();
        } else {
          this.saveDetail(element);
        }
        this.newInfo.set('');
      }
    }
  }

  toggleEditUserMode(action: string = ''): void {
    if (action === 'cancel') {
      this.isEditingUser = !this.isEditingUser;
    } else {
      this.isEditingUser = !this.isEditingUser;
      if (!this.isEditingUser) {
        this.saveUser();
      }
    }
  }

  isAnyEditing(): boolean {
    return this.detailData().some((element) => element.isEditing)
      || this.userData().some((element) => element.isEditing)
      || this.infoData().some((element) => element.isEditing)
      || this.isEditingUser;
  }

  saveDetail(element: any): void {
    this.tokenService.setTokenDetail(this.serial(), element.keyMap.key, element.value, this.infos()).pipe(
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

  deleteInfo(info: string): void {
    const infoKey = info.split(':')[0];
    this.tokenService.deleteInfo(this.serial(), infoKey).pipe(
      switchMap(() => this.showTokenDetail(this.serial())),
      switchMap(() => {
        const infoDetail = this.detailData().find(detail => detail.keyMap.key === 'info');
        if (infoDetail) {
          this.infos.set(this.parseObjectToList(infoDetail.value));
          infoDetail.isEditing = true;
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

  saveUser() {
    if (this.setPinValue !== this.repeatPinValue) {
      console.error('PINs do not match');
      return;
    }
    this.tokenService.assignUser(this.serial(), this.username, this.userRealm, this.setPinValue).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      next: () => {
        this.setPinValue = '';
        this.repeatPinValue = '';
        this.username = '';
        this.userRealm = '';
      },
      error: error => {
        console.error('Failed to assign user', error);
      }
    });
  }

  unassignUser() {
    this.tokenService.unassignUser(this.serial()).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: error => {
        console.error('Failed to unassign user', error);
      }
    });
  }

  setPin() {
    if (this.setPinValue !== this.repeatPinValue) {
      console.error('PINs do not match');
      return;
    }
    this.tokenService.setPin(this.serial(), this.setPinValue).subscribe({
      error: error => {
        console.error('Failed to set pin', error);
      }
    });
  }

  setRandomPin() {
    this.tokenService.setRandomPin(this.serial()).subscribe({
      error: error => {
        console.error('Failed to set random pin', error);
      }
    });
  }

  assignContainer() {
    this.containerService.assignContainer(this.serial(), this.selectedContainer).pipe(
      switchMap(() => this.showTokenDetail(this.serial()))
    ).subscribe({
      error: error => {
        console.error('Failed to assign container', error);
      }
    });
  }

  unassignContainer() {
    this.containerService.unassignContainer(this.serial(), this.selectedContainer).pipe(
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
    console.log("Testing token")
  }

  verifyOTPValue() {
    console.log("Verifying token")
  }
}
