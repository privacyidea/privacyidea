import {Component, computed, effect, Input, signal, WritableSignal} from '@angular/core';
import {NgClass} from '@angular/common';
import {OverflowService} from '../../../services/overflow/overflow.service';
import {MatCell, MatColumnDef, MatRow, MatTableModule} from '@angular/material/table';
import {ContainerService} from '../../../services/container/container.service';
import {forkJoin, Observable, switchMap} from 'rxjs';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatListItem} from '@angular/material/list';
import {TableUtilsService} from '../../../services/table-utils/table-utils.service';
import {EditButtonsComponent} from '../token-details/edit-buttons/edit-buttons.component';
import {MatFormField, MatLabel} from '@angular/material/form-field';
import {MatOption, MatSelect} from '@angular/material/select';
import {RealmService} from '../../../services/realm/realm.service';
import {catchError} from 'rxjs/operators';
import {MatInput} from '@angular/material/input';

export const containerDetailsKeyMap = [
  {key: 'type', label: 'Type'},
  {key: 'states', label: 'Status'},
  {key: 'description', label: 'Description'},
  {key: 'realms', label: 'Realms'},
];

@Component({
  selector: 'app-container-details',
  standalone: true,
  imports: [
    NgClass,
    MatLabel,
    MatTableModule,
    MatCell,
    MatColumnDef,
    MatRow,
    ReactiveFormsModule,
    MatListItem,
    EditButtonsComponent,
    MatFormField,
    MatSelect,
    FormsModule,
    MatOption,
    MatInput,
  ],
  templateUrl: './container-details.component.html',
  styleUrl: './container-details.component.scss'
})
export class ContainerDetailsComponent {
  @Input() serial!: WritableSignal<string>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  isAnyEditing = computed(() => {
    const detailData = this.containerDetailData();

    return (
      detailData.some(element => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo()
    );
  });
  containerDetailData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: WritableSignal<boolean>
  }[]>(containerDetailsKeyMap.map(detail => ({
    keyMap: detail,
    value: '',
    isEditing: signal(false)
  })));
  userData = signal<any>([]);
  selectedRealms = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  userRealm: string = '';

  constructor(protected overflowService: OverflowService,
              protected containerService: ContainerService,
              protected tableUtilsService: TableUtilsService,
              protected realmService: RealmService) {
    effect(() => {
      this.showContainerDetail().subscribe();
    });
  }

  showContainerDetail() {
    return forkJoin([
      this.containerService.getContainerDetails(this.serial()),
      this.realmService.getRealms(),
    ]).pipe(switchMap(([containerDetailsResponse, realms]) => {
        const containerDetails = containerDetailsResponse.result.value.containers[0];
        this.containerDetailData.set(containerDetailsKeyMap.map(detail => ({
          keyMap: detail,
          value: containerDetails[detail.key],
          isEditing: signal(false)
        })).filter(detail => detail.value !== undefined));
        if (containerDetails['users'].length) {
          this.userData.set(containerDetails['users'][0]);
          this.userRealm = this.userData().user_realm;
        }
        this.realmOptions.set(Object.keys(realms.result.value));
        this.selectedRealms.set(containerDetails.realms);
        this.states.set(containerDetails['states']);
        return new Observable<void>(observer => {
          observer.next();
          observer.complete();
        });
      }),
      catchError(error => {
        console.error('Failed to get container details', error);
        throw error;
      })
    );
  }

  isEditableElement(key: string) {
    return key === 'description' ||
      key === 'realms';
  }

  toggleEditMode(element: any, type: string = '', action: string = ''): void {
    if (action === 'cancel') {
      this.handleCancelAction(type);
      element.isEditing.set(!element.isEditing());
      return;
    }

    switch (type) {
      case 'realms':
        this.handleRealms(action);
        break;
      case 'description':
        this.handleDescription(action);
        break;
      default:
        this.handleDefault(element, action);
        break;
    }

    element.isEditing.set(!element.isEditing());
  }

  private handleCancelAction(type: string) {
    switch (type) {
      case 'realms':
        this.selectedRealms.set([]);
        break;
      default:
        this.showContainerDetail().subscribe();
        break;
    }
  }

  private handleRealms(action: string) {
    if (action === 'save') {
      this.saveRealms();
    }
  }

  private handleDescription(action: string) {
    if (action === 'save') {
      this.saveDescription();
    }
  }

  private handleDefault(element: any, action: string) {
    return;
  }

  private saveRealms() {
    this.containerService.setContainerRealm(this.serial(), this.selectedRealms()).pipe(
      switchMap(() => this.showContainerDetail())
    ).subscribe({
      next: () => {
        this.showContainerDetail();
      },
      error: error => {
        console.error('Failed to save token realms', error);
      }
    });
  }

  private saveDescription() {
    const description = this.containerDetailData().find(detail => detail.keyMap.key === 'description')?.value;
    this.containerService.setContainerDescription(this.serial(), description).pipe(
      switchMap(() => this.showContainerDetail())
    ).subscribe({
      next: () => {
        this.showContainerDetail();
      },
      error: error => {
        console.error('Failed to save token description', error);
      }
    });
  }
}
