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
import { forkJoin, Observable, switchMap } from 'rxjs';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { EditButtonsComponent } from '../../token-details/edit-buttons/edit-buttons.component';
import { ContainerService } from '../../../../services/container/container.service';
import { NotificationService } from '../../../../services/notification/notification.service';

@Component({
  selector: 'app-container-details-info',
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
  ],
  templateUrl: './container-details-info.component.html',
  styleUrl: './container-details-info.component.scss',
})
export class ContainerDetailsInfoComponent {
  @Input() containerSerial!: WritableSignal<string>;
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
    private containerService: ContainerService,
    private notificationService: NotificationService,
    protected overflowService: OverflowService,
  ) {}

  toggleInfoEditMode(
    element: any,
    type: string = '',
    action: string = '',
  ): void {
    this.isEditingInfo.set(!this.isEditingInfo());
    if (action === 'cancel') {
      this.newInfo.set({ key: '', value: '' });
    }
    if (action === 'save') {
      this.saveInfo(element.value);
    }
    this.newInfo.set({ key: '', value: '' });
  }

  saveInfo(infos: any): void {
    if (
      this.newInfo().key.trim() !== '' &&
      this.newInfo().value.trim() !== ''
    ) {
      infos[this.newInfo().key] = this.newInfo().value;
    }
    const requests = this.containerService.setContainerInfos(
      this.containerSerial(),
      infos,
    );
    forkJoin(requests).subscribe({
      next: () => {
        this.refreshDetails.set(true);
      },
      error: (error) => {
        console.error('Failed to save container infos.', error);
        this.notificationService.openSnackBar(
          'Failed to save container infos.',
        );
      },
    });
  }

  deleteInfo(key: string): void {
    this.containerService
      .deleteInfo(this.containerSerial(), key)
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
        error: (error) => {
          console.error('Failed to delete info.', error);
          this.notificationService.openSnackBar('Failed to delete info.');
        },
      });
  }
}
