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
import {MatButton, MatFabButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {TokenService} from '../../../services/token/token.service';
import {NgClass} from '@angular/common';
import {MatGridList, MatGridTile} from '@angular/material/grid-list';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatInput, MatSuffix} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatDivider} from '@angular/material/divider';
import {MatSelectModule} from '@angular/material/select';

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
  {key: 'info', label: 'Information'},
  {key: 'realms', label: 'Token Realm'},
  {key: 'tokengroup', label: 'Token Group'},
];

export const userDetail = [
  {key: 'username', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
  {key: 'resolver', label: 'Resolver'},
  {key: 'user_id', label: 'User ID'},
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
    MatButton,
  ],
  templateUrl: './token-details.component.html',
  styleUrl: './token-details.component.css'
})
export class TokenDetailsComponent {
  protected readonly Array = Array;
  protected readonly Object = Object;
  detailData = signal<{ value: any; key: { label: string; key: string }, isEditing: boolean }[]>([]);
  userDetailData = signal<{ value: any; key: { label: string; key: string }, isEditing: boolean }[]>([]);
  infos = signal<string[]>([]);
  newInfo: WritableSignal<string> = signal('');

  constructor(private tokenService: TokenService) {
    effect(() => {
      this.showTokenDetail(this.serial());
    });
  }

  @Input() serial!: WritableSignal<string>
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  hide!: boolean;
  active: boolean = true;
  revoked: boolean = false;

  isObject(value: any): boolean {
    return typeof value === 'object' && value !== null;
  }

  parseObjectToList(value: any): string[] {
    return Object.entries(value).map(([key, val]) => `${key}: ${val}`);
  }

  showTokenDetail(serial: string) {
    this.tokenService.getTokenDetails(serial).subscribe({
      next: response => {
        const tokenDetails = response.result.value.tokens[0];
        this.active = tokenDetails.active;
        this.revoked = tokenDetails.revoked;
        this.detailData.set(details.map(detail => ({
          key: detail,
          value: tokenDetails[detail.key],
          isEditing: false
        })).filter(detail => detail.value !== undefined));

        this.userDetailData.set(userDetail.map(detail => ({
          key: detail,
          value: tokenDetails[detail.key],
          isEditing: false
        })).filter(detail => detail.value !== undefined));
      },
      error: error => {
        console.error('Failed to get token details', error);
      }
    });
  }

  resetFailCount() {
    this.tokenService.resetFailCount(this.serial()).subscribe({
      next: () => {
        this.showTokenDetail(this.serial());
      },
      error: error => {
        console.error('Failed to reset fail counter', error);
      }
    });
  }

  toggleEditMode(element: any, action: string = '') {
    if (action === 'cancel') {
      element.isEditing = false;
    } else {
      element.isEditing = !element.isEditing;
      if (element.isEditing && element.key.key === 'info') {
        this.infos.set(this.parseObjectToList(element.value));
      } else if (!element.isEditing) {
        if (this.newInfo() !== '') {
          this.infos().push(this.newInfo());
        }
        this.saveDetail(element);
        this.newInfo.set('');
      }
    }
  }

  isAnyEditing(): boolean {
    return this.detailData().some((element) => element.isEditing) || this.userDetailData().some((element) => element.isEditing);
  }

  saveDetail(element: any): void {
    this.tokenService.setTokenDetail(this.serial(), element.key.key, element.value, this.infos()).subscribe({
      next: response => {
        this.showTokenDetail(this.serial());
        console.log('Token detail saved:', response);
      },
      error: error => {
        console.error('Failed to save token detail', error);
      }
    });
  }

  deleteToken(): void {
    this.tokenService.deleteToken(this.serial()).subscribe({
      next: () => {
        this.tokenIsSelected.set(false);
      }, error: error => {
        console.error('Failed to delete token', error);
      }
    });
  }

  toggleActive(): void {
    this.tokenService.toggleActive(this.serial(), this.active).subscribe({
      next: () => {
        this.showTokenDetail(this.serial());
      },
      error: error => {
        console.error('Failed to toggle active', error);
      }
    });
  }

  revokeToken(): void {
    this.tokenService.revokeToken(this.serial()).subscribe({
      next: () => {
        this.showTokenDetail(this.serial());
      },
      error: error => {
        console.error('Failed to revoke token', error);
      }
    });
  }

  deleteInfo(info: string) {
    this.tokenService.deleteInfo(this.serial(), info.split(':')[0]).subscribe({
      next: () => {
        this.showTokenDetail(this.serial());
      },
      error: error => {
        console.error('Failed to delete info', error);
      }
    });
  }
}
