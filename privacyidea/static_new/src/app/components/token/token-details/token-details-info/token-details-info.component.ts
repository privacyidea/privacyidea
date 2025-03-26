import {
  Component,
  Input,
  signal,
  Signal,
  WritableSignal,
} from '@angular/core';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTableModule,
} from '@angular/material/table';
import { MatList, MatListItem } from '@angular/material/list';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatDivider } from '@angular/material/divider';
import { TokenService } from '../../../../services/token/token.service';
import { Observable, switchMap } from 'rxjs';
import { EditButtonsComponent } from '../../../shared/edit-buttons/edit-buttons.component';
import { NgClass } from '@angular/common';
import { OverflowService } from '../../../../services/overflow/overflow.service';

@Component({
  selector: 'app-token-details-info',
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatCell,
    MatList,
    MatListItem,
    MatFormField,
    MatInput,
    FormsModule,
    MatIconButton,
    MatLabel,
    MatIcon,
    MatDivider,
    MatRow,
    EditButtonsComponent,
    NgClass,
  ],
  templateUrl: './token-details-info.component.html',
  styleUrl: './token-details-info.component.scss',
})
export class TokenDetailsInfoComponent {
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() infoData!: WritableSignal<
    {
      value: any;
      keyMap: { label: string; key: string };
      isEditing: WritableSignal<boolean>;
    }[]
  >;
  @Input() detailData!: WritableSignal<
    {
      keyMap: { key: string; label: string };
      value: any;
      isEditing: WritableSignal<boolean>;
    }[]
  >;
  @Input() isAnyEditingOrRevoked!: Signal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() refreshDetails!: WritableSignal<boolean>;
  newInfo = signal({ key: '', value: '' });
  protected readonly Object = Object;

  constructor(
    private tokenService: TokenService,
    protected overflowService: OverflowService,
  ) {}

  toggleInfoEdit(): void {
    this.isEditingInfo.update((b) => !b);
    this.newInfo.set({ key: '', value: '' });
  }

  cancelInfoEdit(): void {
    this.isEditingInfo.update((b) => !b);
    this.newInfo.set({ key: '', value: '' });
  }

  saveInfo(element: any): void {
    if (
      this.newInfo().key.trim() !== '' &&
      this.newInfo().value.trim() !== ''
    ) {
      element.value[this.newInfo().key] = this.newInfo().value;
    }
    this.tokenService
      .setTokenInfos(this.tokenSerial(), element.value)
      .subscribe({
        next: () => {
          this.newInfo.set({ key: '', value: '' });
          this.refreshDetails.set(true);
        },
      });
  }

  deleteInfo(key: string): void {
    this.tokenService
      .deleteInfo(this.tokenSerial(), key)
      .pipe(
        switchMap(() => {
          const info = this.detailData().find(
            (detail) => detail.keyMap.key === 'info',
          );
          if (info) {
            this.isEditingInfo.set(true);
          }
          return new Observable<void>((observer) => {
            observer.next();
            observer.complete();
          });
        }),
      )
      .subscribe({
        next: () => {
          this.refreshDetails.set(true);
        },
      });
  }
}
