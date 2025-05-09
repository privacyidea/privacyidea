import {
  Component,
  Input,
  linkedSignal,
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
import { EditButtonsComponent } from '../../../shared/edit-buttons/edit-buttons.component';
import { ContainerService } from '../../../../services/container/container.service';

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
  protected readonly Object = Object;
  containerSerial = this.containerService.containerSerial;
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
  newInfo: WritableSignal<{ key: string; value: string }> = linkedSignal({
    source: () => this.isEditingInfo,
    computation: () => {
      return { key: '', value: '' };
    },
  });

  constructor(
    private containerService: ContainerService,
    protected overflowService: OverflowService,
  ) {}

  toggleInfoEdit(): void {
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
    const requests = this.containerService.setContainerInfos(
      this.containerSerial(),
      element.value,
    );
    forkJoin(requests).subscribe({
      next: () => {
        this.newInfo.set({ key: '', value: '' });
        this.containerService.containerDetailResource.reload();
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
          this.containerService.containerDetailResource.reload();
        },
      });
  }
}
