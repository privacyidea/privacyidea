import {
  Component,
  computed,
  Input,
  signal,
  WritableSignal,
} from '@angular/core';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTable,
  MatTableModule,
} from '@angular/material/table';
import { MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatListItem } from '@angular/material/list';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';
import { NgClass } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatInput } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { forkJoin, Observable, single, switchMap } from 'rxjs';
import { RealmService } from '../../../services/realm/realm.service';
import { catchError } from 'rxjs/operators';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { TokenDetailsUserComponent } from './token-details-user/token-details-user.component';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { TokenDetailsInfoComponent } from './token-details-info/token-details-info.component';
import { TokenDetailsActionsComponent } from './token-details-actions/token-details-actions.component';
import { EditButtonsComponent } from '../../shared/edit-buttons/edit-buttons.component';
import { OverflowService } from '../../../services/overflow/overflow.service';
import { MatDivider } from '@angular/material/divider';
import { NotificationService } from '../../../services/notification/notification.service';
import { TokenSelectedContent } from '../token.component';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';

export const tokenDetailsKeyMap = [
  { key: 'tokentype', label: 'Type' },
  { key: 'active', label: 'Status' },
  { key: 'maxfail', label: 'Max Count' },
  { key: 'failcount', label: 'Fail Count' },
  { key: 'rollout_state', label: 'Rollout State' },
  { key: 'otplen', label: 'OTP Length' },
  { key: 'count_window', label: 'Count Window' },
  { key: 'sync_window', label: 'Sync Window' },
  { key: 'count', label: 'Count' },
  { key: 'description', label: 'Description' },
  { key: 'realms', label: 'Token Realms' },
  { key: 'tokengroup', label: 'Token Groups' },
  { key: 'container_serial', label: 'Container Serial' },
];

export const userDetailsKeyMap = [
  { key: 'user_realm', label: 'User Realm' },
  { key: 'username', label: 'User' },
  { key: 'resolver', label: 'Resolver' },
  { key: 'user_id', label: 'User ID' },
];

export const infoDetailsKeyMap = [{ key: 'info', label: 'Information' }];

@Component({
  selector: 'app-token-details',
  standalone: true,
  imports: [
    MatCell,
    MatTableModule,
    MatColumnDef,
    MatIcon,
    MatListItem,
    MatRow,
    MatTable,
    NgClass,
    FormsModule,
    MatInput,
    MatFormFieldModule,
    MatSelectModule,
    ReactiveFormsModule,
    MatIconButton,
    TokenDetailsUserComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    EditButtonsComponent,
    MatDivider,
    CopyButtonComponent,
  ],
  templateUrl: './token-details.component.html',
  styleUrl: './token-details.component.scss',
})
export class TokenDetailsComponent {
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  setPinValue = signal('');
  repeatPinValue = signal('');
  realmOptions = signal<string[]>([]);
  tokenDetailData = signal<
    {
      value: any;
      keyMap: { label: string; key: string };
      isEditing: WritableSignal<boolean>;
    }[]
  >(
    tokenDetailsKeyMap.map((detail) => ({
      keyMap: detail,
      value: '',
      isEditing: signal(false),
    })),
  );
  infoData = signal<
    {
      value: any;
      keyMap: { label: string; key: string };
      isEditing: WritableSignal<boolean>;
    }[]
  >(
    infoDetailsKeyMap.map((detail) => ({
      keyMap: detail,
      value: '',
      isEditing: signal(false),
    })),
  );
  userData = signal<
    {
      value: any;
      keyMap: { label: string; key: string };
      isEditing: WritableSignal<boolean>;
    }[]
  >(
    userDetailsKeyMap.map((detail) => ({
      keyMap: detail,
      value: '',
      isEditing: signal(false),
    })),
  );
  isAnyEditingOrRevoked = computed(() => {
    const detailData = this.tokenDetailData();

    return (
      detailData.some((element) => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo() ||
      this.revoked()
    );
  });
  containerOptions = signal<string[]>([]);
  tokengroupOptions = signal<string[]>([]);
  selectedContainer = signal<string>('');
  filteredContainerOptions = computed(() => {
    const filter = (this.selectedContainer() || '').toLowerCase();
    return this.containerOptions().filter((option) =>
      option.toLowerCase().includes(filter),
    );
  });
  selectedRealms = signal<string[]>([]);
  selectedTokengroup = signal<string[]>([]);
  userRealm: string = '';
  maxfail: number = 0;
  protected readonly single = single;

  constructor(
    private tokenService: TokenService,
    private containerService: ContainerService,
    private realmService: RealmService,
    private notificationService: NotificationService,
    protected overflowService: OverflowService,
    protected tableUtilsService: TableUtilsService,
  ) {}

  ngAfterViewInit() {
    this.showTokenDetail().subscribe();
  }

  isObject(value: any): boolean {
    return typeof value === 'object' && value !== null;
  }

  showTokenDetail(): Observable<void> {
    return forkJoin([
      this.tokenService.getTokenDetails(this.tokenSerial()),
      this.realmService.getRealms(),
    ]).pipe(
      switchMap(([tokenDetailsResponse, realms]) => {
        const tokenDetails = tokenDetailsResponse.result.value.tokens[0];
        this.active.set(tokenDetails.active);
        this.revoked.set(tokenDetails.revoked);
        this.maxfail = tokenDetails.maxfail;
        this.selectedContainer.set(tokenDetails.container_serial);
        this.tokenDetailData.set(
          tokenDetailsKeyMap
            .map((detail) => ({
              keyMap: detail,
              value: tokenDetails[detail.key],
              isEditing: signal(false),
            }))
            .filter((detail) => detail.value !== undefined),
        );
        this.userData.set(
          userDetailsKeyMap
            .map((detail) => ({
              keyMap: detail,
              value: tokenDetails[detail.key],
              isEditing: signal(false),
            }))
            .filter((detail) => detail.value !== undefined),
        );

        this.infoData.set(
          infoDetailsKeyMap
            .map((detail) => ({
              keyMap: detail,
              value: tokenDetails[detail.key],
              isEditing: signal(false),
            }))
            .filter((detail) => detail.value !== undefined),
        );

        this.realmOptions.set(Object.keys(realms.result.value));
        this.selectedRealms.set(tokenDetails.realms);
        this.userRealm = this.userData().find(
          (detail) => detail.keyMap.key === 'user_realm',
        )?.value;
        return new Observable<void>((observer) => {
          observer.next();
          observer.complete();
        });
      }),
      catchError((error) => {
        console.error('Failed to get token details.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to get token details. ' + message,
        );
        throw error;
      }),
    );
  }

  resetFailCount(): void {
    this.tokenService
      .resetFailCount(this.tokenSerial())
      .pipe(switchMap(() => this.showTokenDetail()));
  }

  toggleEditMode(element: any, type: string = '', action: string = ''): void {
    if (action === 'cancel') {
      this.handleCancelAction(type);
      element.isEditing.set(!element.isEditing());
      return;
    }

    switch (type) {
      case 'container_serial':
        this.handleContainerSerial(action);
        break;
      case 'tokengroup':
        this.handleTokengroup(action);
        break;
      case 'realms':
        this.handleRealms(action);
        break;
      default:
        this.handleDefault(element, action);
        break;
    }

    element.isEditing.set(!element.isEditing());
  }

  saveDetail(key: string, value: string): void {
    this.tokenService
      .setTokenDetail(this.tokenSerial(), key, value)
      .pipe(switchMap(() => this.showTokenDetail()))
      .subscribe({
        next: () => {
          this.showTokenDetail();
        },
      });
  }

  saveContainer() {
    this.containerService
      .assignContainer(this.tokenSerial(), this.selectedContainer())
      .pipe(switchMap(() => this.showTokenDetail()));
  }

  deleteContainer() {
    this.containerService
      .unassignContainer(this.tokenSerial(), this.selectedContainer())
      .pipe(switchMap(() => this.showTokenDetail()));
  }

  isEditableElement(key: any) {
    return (
      key === 'maxfail' ||
      key === 'count_window' ||
      key === 'sync_window' ||
      key === 'description' ||
      key === 'info' ||
      key === 'realms' ||
      key === 'tokengroup' ||
      key === 'container_serial'
    );
  }

  isNumberElement(key: any) {
    return key === 'maxfail' || key === 'count_window' || key === 'sync_window';
  }

  containerSelected(containerSerial: string) {
    this.isProgrammaticChange.set(true);
    this.selectedContent.set('container_details');
    this.containerSerial.set(containerSerial);
  }

  private handleContainerSerial(action: string): void {
    if (this.containerOptions().length === 0) {
      this.containerService.getContainerData({ noToken: true }).subscribe({
        next: (containers: any) => {
          this.containerOptions.set(
            Object.values(
              containers.result.value.containers as {
                serial: string;
              }[],
            ).map((container) => container.serial),
          );
          this.selectedContainer.set(this.selectedContainer());
        },
      });
    }
    if (action === 'save') {
      this.selectedContainer.set(this.selectedContainer().trim() ?? null);
      this.saveContainer();
    }
  }

  private handleTokengroup(action: string): void {
    if (this.tokengroupOptions().length === 0) {
      this.tokenService.getTokengroups().subscribe({
        next: (tokengroups: any) => {
          this.tokengroupOptions.set(Object.keys(tokengroups.result.value));
          this.selectedTokengroup.set(
            this.tokenDetailData().find(
              (detail) => detail.keyMap.key === 'tokengroup',
            )?.value,
          );
        },
      });
    }
    if (action === 'save') {
      this.saveTokengroup(this.selectedTokengroup());
    }
  }

  private handleRealms(action: string): void {
    if (action === 'save') {
      this.saveRealms();
    }
  }

  private handleDefault(element: any, action: string): void {
    if (action === 'save') {
      this.saveDetail(element.keyMap.key, element.value);
    }
  }

  private handleCancelAction(type: string): void {
    switch (type) {
      case 'container_serial':
        this.selectedContainer.set('');
        break;
      case 'tokengroup':
        this.selectedTokengroup.set(
          this.tokenDetailData().find(
            (detail) => detail.keyMap.key === 'tokengroup',
          )?.value,
        );
        break;
      case 'realms':
        this.selectedRealms.set(
          this.tokenDetailData().find(
            (detail) => detail.keyMap.key === 'realms',
          )?.value,
        );
        break;
      default:
        this.showTokenDetail().subscribe();
        break;
    }
  }

  private saveRealms() {
    this.tokenService
      .setTokenRealm(this.tokenSerial(), this.selectedRealms())
      .pipe(switchMap(() => this.showTokenDetail()))
      .subscribe({
        next: () => {
          this.showTokenDetail();
        },
      });
  }

  private saveTokengroup(value: any) {
    this.tokenService
      .setTokengroup(this.tokenSerial(), value)
      .pipe(switchMap(() => this.showTokenDetail()))
      .subscribe({
        next: () => {
          this.showTokenDetail();
        },
      });
  }
}
