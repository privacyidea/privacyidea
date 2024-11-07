import {Component, effect, Input, signal, WritableSignal} from '@angular/core';
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatRow,
  MatRowDef,
  MatTable
} from '@angular/material/table';
import {MatFabButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {TokenService} from '../../../services/token/token.service';
import {NgClass} from '@angular/common';

export const details = [
  {key: 'tokentype', label: 'Type'},
  {key: 'active', label: 'Active'},
  {key: 'maxfail', label: 'Max Count'},
  {key: 'failcount', label: 'Count'},
  {key: 'otplen', label: 'OTP Length'},
  {key: 'count_window', label: 'Count Window'},
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
    NgClass
  ],
  templateUrl: './token-details.component.html',
  styleUrl: './token-details.component.css'
})
export class TokenDetailsComponent {
  protected readonly Array = Array;
  protected readonly Object = Object;
  detailData = signal<{ value: any; key: { label: string; key: string } }[]>([]);
  userDetailData = signal<{ value: any; key: { label: string; key: string } }[]>([]);

  constructor(private tokenService: TokenService) {
    effect(() => {
      this.showTokenDetail(this.serial());
    });
  }

  @Input() serial!: WritableSignal<string>

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
        this.detailData.set(details.map(detail => ({
          key: detail,
          value: tokenDetails[detail.key]
        })).filter(detail => detail.value !== undefined));

        this.userDetailData.set(userDetail.map(detail => ({
          key: detail,
          value: tokenDetails[detail.key]
        })).filter(detail => detail.value !== undefined));
      },
      error: error => {
        console.error('Failed to get token details', error);
      }
    });
  }

  editTokenDetail() {
    console.log('Edit button clicked. Implement your edit logic here.');
  }
}
