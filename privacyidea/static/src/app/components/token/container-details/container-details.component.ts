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
import {MatAutocomplete, MatAutocompleteTrigger} from '@angular/material/autocomplete';
import {MatIcon} from '@angular/material/icon';
import {MatIconButton} from '@angular/material/button';
import {UserService} from '../../../services/user/user.service';
import {infoDetailsKeyMap} from '../token-details/token-details.component';
import {
  ContainerDetailsInfoComponent
} from './container-details-info/container-details-info.component';

export const containerDetailsKeyMap = [
  {key: 'type', label: 'Type'},
  {key: 'states', label: 'Status'},
  {key: 'description', label: 'Description'},
  {key: 'realms', label: 'Realms'},
];

const containerUserDetailsKeyMap = [
  {key: 'user_realm', label: 'User Realm'},
  {key: 'user_name', label: 'User'},
  {key: 'user_resolver', label: 'Resolver'},
  {key: 'user_id', label: 'User ID'},
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
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatIcon,
    MatIconButton,
    ContainerDetailsInfoComponent,
  ],
  templateUrl: './container-details.component.html',
  styleUrl: './container-details.component.scss'
})
export class ContainerDetailsComponent {
  @Input() serial!: WritableSignal<string>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() selectedUsername = signal<string>('');
  userOptions = signal<string[]>([]);
  selectedUserRealm = signal<string>('');
  filteredUserOptions = signal<string[]>([]);
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
  infoData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: WritableSignal<boolean>
  }[]>(infoDetailsKeyMap.map(detail => ({
    keyMap: detail,
    value: '',
    isEditing: signal(false)
  })));
  userData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: WritableSignal<boolean>
  }[]>([]);
  selectedRealms = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  userRealm: string = '';

  constructor(protected overflowService: OverflowService,
              protected containerService: ContainerService,
              protected tableUtilsService: TableUtilsService,
              protected realmService: RealmService,
              protected userService: UserService) {
    effect(() => {
      this.showContainerDetail().subscribe();
    });

    effect(() => {
      const value = this.selectedUsername();
      const filteredOptions = this._filterUserOptions(value || '');
      this.filteredUserOptions.set(filteredOptions);
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
  }

  private _filterUserOptions(value: string): string[] {
    const filterValue = value.toLowerCase();
    return this.userOptions().filter(option => option.toLowerCase().includes(filterValue));
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

        this.infoData.set(infoDetailsKeyMap.map(detail => ({
          keyMap: detail,
          value: containerDetails[detail.key],
          isEditing: signal(false)
        })).filter(detail => detail.value !== undefined));


        let user = {
          user_realm: '',
          user_name: '',
          user_resolver: '',
          user_id: ''
        };
        if (containerDetails['users'].length) {
          user = containerDetails['users'][0];
        }
        this.userData.set(containerUserDetailsKeyMap.map(detail => ({
          keyMap: detail,
          value: user[detail.key as keyof typeof user],
          isEditing: signal(false)
        })).filter(detail => detail.value !== undefined));
        this.userRealm = this.userData().find(
          detail => detail.keyMap.key === 'user_realm')?.value;
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
      if (type === 'user_name') {
        this.isEditingUser.set(!this.isEditingUser());
        return;
      }
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
      case 'user_name':
        this.isEditingUser.set(!this.isEditingUser());
        this.handleUser(action);
        return;
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

  private handleUser(action: string) {
    if (action === 'save') {
      this.saveUser();
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

  saveUser() {
this.containerService.assignUser(this.serial(), this.selectedUsername(), this.userRealm).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
      error: error => {
        console.error('Failed to assign user', error);
      }
    });
  }

  unassignUser() {
    this.containerService.unassignUser(this.serial(), this.userData().find(
      detail => detail.keyMap.key === 'user_name')?.value,
      this.userData().find(detail => detail.keyMap.key === 'user_realm')?.value
    ).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
      error: error => {
        console.error('Failed to unassign user', error);
      }
    });
  }
}
