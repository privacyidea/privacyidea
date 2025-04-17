import {
  Component,
  computed,
  effect,
  ElementRef,
  Input,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { NgClass } from '@angular/common';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { ContainerService } from '../../../services/container/container.service';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatListItem } from '@angular/material/list';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { EditButtonsComponent } from '../../shared/edit-buttons/edit-buttons.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { RealmService } from '../../../services/realm/realm.service';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { infoDetailsKeyMap } from '../token-details/token-details.component';
import { ContainerDetailsInfoComponent } from './container-details-info/container-details-info.component';
import { ContainerDetailsTokenTableComponent } from './container-details-token-table/container-details-token-table.component';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { TokenService } from '../../../services/token/token.service';
import { MatDivider } from '@angular/material/divider';
import { MatCheckbox } from '@angular/material/checkbox';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { UserService } from '../../../services/user/user.service';
import { OverflowService } from '../../../services/overflow/overflow.service';
import { TokenSelectedContent } from '../token.component';

export const containerDetailsKeyMap = [
  { key: 'type', label: 'Type' },
  { key: 'states', label: 'Status' },
  { key: 'description', label: 'Description' },
  { key: 'realms', label: 'Realms' },
];

const containerUserDetailsKeyMap = [
  { key: 'user_realm', label: 'User Realm' },
  { key: 'user_name', label: 'User' },
  { key: 'user_resolver', label: 'Resolver' },
  { key: 'user_id', label: 'User ID' },
];

interface TokenOption {
  serial: string;
  tokentype: string;
  active: boolean;
  username: string;
}

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
    FormsModule,
    MatSelectModule,
    MatInput,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatIcon,
    MatIconButton,
    ContainerDetailsInfoComponent,
    ContainerDetailsTokenTableComponent,
    MatPaginator,
    MatDivider,
    MatCheckbox,
    CopyButtonComponent,
  ],
  templateUrl: './container-details.component.html',
  styleUrls: ['./container-details.component.scss'],
})
export class ContainerDetailsComponent {
  states = this.containerService.states;
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  tokenSerial = this.tokenService.tokenSerial;
  containerSerial = this.tokenService.containerSerial;
  showOnlyTokenNotInContainer = this.tokenService.showOnlyTokenNotInContainer;
  filterValue = this.tokenService.filterValue;

  tokenResource = this.tokenService.tokenResource;
  pageIndex = this.tokenService.pageIndex;
  pageSize = 10;
  tokenDataSource: WritableSignal<MatTableDataSource<any>> = linkedSignal({
    source: this.tokenResource.value,
    computation: (tokenResource, previous) => {
      if (tokenResource) {
        return new MatTableDataSource(tokenResource.result.value.tokens);
      }
      return previous?.value ?? new MatTableDataSource();
    },
  });
  total: WritableSignal<number> = linkedSignal({
    source: this.tokenResource.value,
    computation: (tokenResource, previous) => {
      if (tokenResource) {
        return tokenResource.result.value.count;
      }
      return previous?.value ?? 0;
    },
  });

  containerDetailResource = this.containerService.containerDetailResource;
  containerDetails = linkedSignal({
    source: this.containerDetailResource.value,
    computation: (containerDetailResourceValue) =>
      containerDetailResourceValue
        ? containerDetailResourceValue.result.value.containers[0]
        : null,
  });
  containerDetailData = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => {
      if (!containerDetails) {
        return containerDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: '',
          isEditing: signal(false),
        }));
      }
      return containerDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: containerDetails[detail.key],
          isEditing: signal(false),
        }))
        .filter((detail) => detail.value !== undefined);
    },
  });
  infoData = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => {
      if (!containerDetails) {
        return infoDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: '',
          isEditing: signal(false),
        }));
      }
      return infoDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: containerDetails[detail.key],
          isEditing: signal(false),
        }))
        .filter((detail) => detail.value !== undefined);
    },
  });
  containerTokenData = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails, previous) => {
      if (!containerDetails) {
        return previous?.value ?? new MatTableDataSource([]);
      }
      return new MatTableDataSource(containerDetails.tokens ?? []);
    },
  });
  selectedRealms = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => containerDetails?.realms || [],
  });
  rawUserData = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => {
      if (
        !containerDetails ||
        !Array.isArray(containerDetails.users) ||
        containerDetails.users.length === 0
      ) {
        return {
          user_realm: '',
          user_name: '',
          user_resolver: '',
          user_id: '',
        };
      }
      return containerDetails.users[0];
    },
  });
  userData = linkedSignal({
    source: this.rawUserData,
    computation: (user) => {
      return containerUserDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: user[detail.key as keyof typeof user],
          isEditing: signal(false),
        }))
        .filter((detail) => detail.value !== undefined);
    },
  });
  userRealm = linkedSignal({
    source: this.rawUserData,
    computation: (user) => user.user_realm || '',
  });

  isAnyEditing = computed(() => {
    return (
      this.containerDetailData().some((element) => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo()
    );
  });

  @ViewChild('filterHTMLInputElement')
  filterHTMLInputElement!: ElementRef<HTMLInputElement>;
  @ViewChild('tokenAutoTrigger', { read: MatAutocompleteTrigger })
  tokenAutoTrigger!: MatAutocompleteTrigger;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;

  constructor(
    protected overflowService: OverflowService,
    protected containerService: ContainerService,
    protected tableUtilsService: TableUtilsService,
    protected realmService: RealmService,
    protected tokenService: TokenService,
    protected userService: UserService,
  ) {
    effect(() => {
      this.showOnlyTokenNotInContainer();
      if (this.filterHTMLInputElement) {
        this.filterHTMLInputElement.nativeElement.focus();
      }
    });
  }

  isEditableElement(key: string) {
    return key === 'description' || key === 'realms';
  }

  cancelContainerEdit(element: any) {
    switch (element.keyMap.key) {
      case 'realms':
        this.selectedRealms.set([]);
        break;
      case 'user_name':
        this.isEditingUser.update((b) => !b);
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  saveContainerEdit(element: any) {
    switch (element.keyMap.key) {
      case 'realms':
        this.saveRealms();
        break;
      case 'description':
        this.saveDescription();
        break;
      case 'user_name':
        this.saveUser();
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  toggleContainerEdit(element: any) {
    switch (element.keyMap.key) {
      case 'user_name':
        this.isEditingUser.update((b) => !b);
        if (this.isEditingUser() && !this.userService.selectedUserRealm()) {
          this.realmService.defaultRealmResource.reload();
        }
        return;
      default:
        element.isEditing.set(!element.isEditing());
    }
  }

  saveUser() {
    this.containerService
      .assignUser({
        containerSerial: this.containerSerial(),
        username: this.userService.selectedUsername(),
        userRealm: this.userService.selectedUserRealm(),
      })
      .subscribe({
        next: () => {
          this.userService.selectedUsername.set('');
          this.userService.selectedUserRealm.set('');
          this.isEditingUser.update((b) => !b);
          this.containerDetailResource.reload();
        },
      });
  }

  unassignUser() {
    const userName = this.userData().find(
      (d) => d.keyMap.key === 'user_name',
    )?.value;
    const userRealm = this.userData().find(
      (d) => d.keyMap.key === 'user_realm',
    )?.value;
    this.containerService
      .unassignUser(this.containerSerial(), userName ?? '', userRealm ?? '')
      .subscribe({
        next: () => {
          this.containerDetailResource.reload();
        },
      });
  }

  onPageEvent(event: PageEvent) {
    this.tokenService.eventPageSize = event.pageSize;
    this.pageIndex.set(event.pageIndex);
    setTimeout(() => {
      this.filterHTMLInputElement.nativeElement.focus();
      this.tokenAutoTrigger.openPanel();
    }, 0);
  }

  onFilterEvent(newFilter: string) {
    if (this.showOnlyTokenNotInContainer()) {
      newFilter = newFilter + ' container_serial:';
    }
    this.filterValue.set(newFilter);
  }

  addTokenToContainer(option: TokenOption) {
    this.containerService
      .addTokenToContainer(this.containerSerial(), option['serial'])
      .subscribe({
        next: () => {
          this.containerDetailResource.reload();
          this.tokenService.tokenResource.reload();
        },
      });
  }

  saveRealms() {
    this.containerService
      .setContainerRealm(this.containerSerial(), this.selectedRealms())
      .subscribe({
        next: () => {
          this.containerDetailResource.reload();
        },
      });
  }

  saveDescription() {
    const description = this.containerDetailData().find(
      (detail) => detail.keyMap.key === 'description',
    )?.value;
    this.containerService
      .setContainerDescription(this.containerSerial(), description)
      .subscribe({
        next: () => {
          this.containerDetailResource.reload();
        },
      });
  }
}
