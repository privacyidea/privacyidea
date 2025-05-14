import {
  Component,
  computed,
  effect,
  linkedSignal,
  signal,
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
import { RealmService } from '../../../services/realm/realm.service';
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
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { ContentService } from '../../../services/content/content.service';
import { AuthService } from '../../../services/auth/auth.service';

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
  styleUrls: ['./token-details.component.scss'],
})
export class TokenDetailsComponent {
  tokenIsActive = this.tokenService.tokenIsActive;
  tokenIsRevoked = this.tokenService.tokenIsRevoked;
  selectedContent = this.contentService.selectedContent;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;
  containerSerial = this.containerService.containerSerial;
  tokenSerial = this.tokenService.tokenSerial;
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  setPinValue = signal('');
  repeatPinValue = signal('');

  tokenDetailResource = this.tokenService.tokenDetailResource;
  tokenDetails = linkedSignal({
    source: this.tokenDetailResource.value,
    computation: (res) => (res ? res.result.value.tokens[0] : null),
  });
  tokenDetailData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return tokenDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: '',
          isEditing: signal(false),
        }));
      }
      return tokenDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: details[detail.key],
          isEditing: signal(false),
        }))
        .filter((detail) => detail.value !== undefined);
    },
  });
  infoData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return infoDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: '',
          isEditing: signal(false),
        }));
      }
      return infoDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: details[detail.key],
          isEditing: signal(false),
        }))
        .filter((detail) => detail.value !== undefined);
    },
  });
  userData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return userDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: '',
          isEditing: signal(false),
        }));
      }
      return userDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: details[detail.key],
          isEditing: signal(false),
        }))
        .filter((detail) => detail.value !== undefined);
    },
  });
  tokengroupOptions = signal<string[]>([]);
  selectedTokengroup = signal<string[]>([]);
  tokenType = linkedSignal({
    source: this.tokenDetails,
    computation: () => this.tokenDetails()?.tokentype ?? '',
  });
  userRealm = '';
  maxfail = 0;
  isAnyEditingOrRevoked = computed(() => {
    return (
      this.tokenDetailData().some((element) => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo() ||
      this.tokenIsRevoked()
    );
  });

  constructor(
    protected tokenService: TokenService,
    protected containerService: ContainerService,
    protected realmService: RealmService,
    protected overflowService: OverflowService,
    protected tableUtilsService: TableUtilsService,
    protected contentService: ContentService,
    private authService: AuthService,
  ) {
    effect(() => {
      if (!this.tokenDetails()) return;
      this.tokenIsActive.set(this.tokenDetails().active);
      this.tokenIsRevoked.set(this.tokenDetails().revoked);
      this.maxfail = this.tokenDetails().maxfail;
      this.containerService.selectedContainer.set(
        this.tokenDetails().container_serial,
      );
      this.realmService.selectedRealms.set(this.tokenDetails().realms);
      this.userRealm =
        this.userData().find((detail) => detail.keyMap.key === 'user_realm')
          ?.value || '';
    });
  }

  isObject(value: any): boolean {
    return typeof value === 'object' && value !== null;
  }

  resetFailCount(): void {
    this.tokenService.resetFailCount(this.tokenSerial()).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      },
    });
  }

  cancelTokenEdit(element: any) {
    this.resetEdit(element.keyMap.key);
    element.isEditing.set(!element.isEditing());
  }

  saveTokenEdit(element: any) {
    switch (element.keyMap.key) {
      case 'container_serial':
        this.containerService.selectedContainer.set(
          this.containerService.selectedContainer().trim() ?? null,
        );
        this.saveContainer();
        break;
      case 'tokengroup':
        this.saveTokengroup(this.selectedTokengroup());
        break;
      case 'realms':
        this.saveRealms();
        break;
      default:
        this.saveTokenDetail(element.keyMap.key, element.value);
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  toggleTokenEdit(element: any): void {
    switch (element.keyMap.key) {
      case 'tokengroup':
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
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  saveTokenDetail(key: string, value: string): void {
    this.tokenService
      .saveTokenDetail(this.tokenSerial(), key, value)
      .subscribe({
        next: () => {
          this.tokenDetailResource.reload();
        },
      });
  }

  saveContainer() {
    this.containerService
      .assignContainer(
        this.tokenSerial(),
        this.containerService.selectedContainer(),
      )
      .subscribe({
        next: () => {
          this.tokenDetailResource.reload();
        },
      });
  }

  deleteContainer() {
    this.containerService
      .unassignContainer(
        this.tokenSerial(),
        this.containerService.selectedContainer(),
      )
      .subscribe({
        next: () => {
          this.tokenDetailResource.reload();
        },
      });
  }

  isEditableElement(key: any) {
    const role = this.authService.role();
    if (role === 'admin') {
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
    } else {
      return key === 'description';
    }
  }

  isNumberElement(key: any) {
    return key === 'maxfail' || key === 'count_window' || key === 'sync_window';
  }

  containerSelected(containerSerial: string) {
    this.isProgrammaticTabChange.set(true);
    this.selectedContent.set('container_details');
    this.containerSerial.set(containerSerial);
  }

  private resetEdit(type: string): void {
    switch (type) {
      case 'container_serial':
        this.containerService.selectedContainer.set('');
        break;
      case 'tokengroup':
        this.selectedTokengroup.set(
          this.tokenDetailData().find(
            (detail) => detail.keyMap.key === 'tokengroup',
          )?.value,
        );
        break;
      case 'realms':
        this.realmService.selectedRealms.set(
          this.tokenDetailData().find(
            (detail) => detail.keyMap.key === 'realms',
          )?.value,
        );
        break;
      default:
        this.tokenDetailResource.reload();
        break;
    }
  }

  private saveRealms() {
    this.tokenService
      .setTokenRealm(this.tokenSerial(), this.realmService.selectedRealms())
      .subscribe({
        next: () => {
          this.tokenDetailResource.reload();
        },
      });
  }

  private saveTokengroup(value: any) {
    this.tokenService.setTokengroup(this.tokenSerial(), value).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      },
    });
  }
}
