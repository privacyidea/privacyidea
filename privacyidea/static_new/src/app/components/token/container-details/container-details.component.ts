import {
  Component,
  computed,
  effect,
  ElementRef,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { NgClass } from '@angular/common';
import { OverflowService } from '../../../services/overflow/overflow.service';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { ContainerService } from '../../../services/container/container.service';
import { forkJoin, Observable, switchMap } from 'rxjs';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatListItem } from '@angular/material/list';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { EditButtonsComponent } from '../token-details/edit-buttons/edit-buttons.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatOption, MatSelect } from '@angular/material/select';
import { RealmService } from '../../../services/realm/realm.service';
import { catchError } from 'rxjs/operators';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { UserService } from '../../../services/user/user.service';
import { infoDetailsKeyMap } from '../token-details/token-details.component';
import { ContainerDetailsInfoComponent } from './container-details-info/container-details-info.component';
import { ContainerDetailsTokenTableComponent } from './container-details-token-table/container-details-token-table.component';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { TokenService } from '../../../services/token/token.service';
import { MatDivider } from '@angular/material/divider';
import { MatCheckbox } from '@angular/material/checkbox';
import { NotificationService } from '../../../services/notification/notification.service';
import { CdkCopyToClipboard } from '@angular/cdk/clipboard';

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
    MatSelect,
    FormsModule,
    MatOption,
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
    CdkCopyToClipboard,
  ],
  templateUrl: './container-details.component.html',
  styleUrl: './container-details.component.scss',
})
export class ContainerDetailsComponent {
  @Input() selectedContent!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() selectedUsername = signal<string>('');
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  userOptions = signal<string[]>([]);
  selectedUserRealm = signal<string>('');
  filteredUserOptions = signal<string[]>([]);
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  containerDetailData = signal<
    {
      value: any;
      keyMap: { label: string; key: string };
      isEditing: WritableSignal<boolean>;
    }[]
  >(
    containerDetailsKeyMap.map((detail) => ({
      keyMap: detail,
      value: '',
      isEditing: signal(false),
    })),
  );
  isAnyEditing = computed(() => {
    const detailData = this.containerDetailData();

    return (
      detailData.some((element) => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo()
    );
  });
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
  >([]);
  tokenOptions = signal<TokenOption[]>([]);
  selectedRealms = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  tokenToAddFilter = signal('');
  showOnlyTokenNotInContainer = signal(true);
  containerTokenData = signal<MatTableDataSource<any>>(
    new MatTableDataSource<any>([]),
  );
  userRealm: string = '';
  length = 0;
  pageIndex = 0;
  pageSize = 10;
  pageSizeOptions = [10];
  filterValue = '';

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild('tokenFilterInput')
  tokenFilterInput!: ElementRef<HTMLInputElement>;
  @ViewChild('tokenAutoTrigger', { read: MatAutocompleteTrigger })
  tokenAutoTrigger!: MatAutocompleteTrigger;

  constructor(
    protected overflowService: OverflowService,
    protected containerService: ContainerService,
    protected tableUtilsService: TableUtilsService,
    protected realmService: RealmService,
    protected userService: UserService,
    protected tokenService: TokenService,
    private notificationService: NotificationService,
  ) {
    effect(() => {
      const value = this.selectedUsername();
      const filteredOptions = this._filterUserOptions(value || '');
      this.filteredUserOptions.set(filteredOptions);
    });

    effect(() => {
      if (this.selectedUserRealm()) {
        this.userService.getUsers(this.selectedUserRealm()).subscribe({
          next: (users: any) => {
            this.userOptions.set(
              users.result.value.map((user: any) => user.username),
            );
          },
          error: (error) => {
            console.error('Failed to get users.', error);
            const message = error.error?.result?.error?.message || '';
            this.notificationService.openSnackBar(
              'Failed to get users. ' + message,
            );
          },
        });
      }
    });

    effect(() => {
      this.filterValue = this.filterValue.replace(/container_serial:\S*/g, '');
      if (this.showOnlyTokenNotInContainer()) {
        this.filterValue = this.filterValue + ' container_serial:';
      }
      this.pageIndex = 0;
      this.fetchTokenData();
    });
  }

  ngAfterViewInit() {
    this.showContainerDetail().subscribe();
  }

  showContainerDetail() {
    return forkJoin([
      this.containerService.getContainerDetails(this.containerSerial()),
      this.realmService.getRealms(),
      this.tokenService.getTokenData(
        this.paginator.pageIndex,
        this.paginator.pageSize,
        undefined,
        this.tokenToAddFilter().trim() + ' container_serial:',
      ),
    ]).pipe(
      switchMap(([containerDetailsResponse, realms, tokens]) => {
        const containerDetails =
          containerDetailsResponse.result.value.containers[0];
        this.containerDetailData.set(
          containerDetailsKeyMap
            .map((detail) => ({
              keyMap: detail,
              value: containerDetails[detail.key],
              isEditing: signal(false),
            }))
            .filter((detail) => detail.value !== undefined),
        );

        this.infoData.set(
          infoDetailsKeyMap
            .map((detail) => ({
              keyMap: detail,
              value: containerDetails[detail.key],
              isEditing: signal(false),
            }))
            .filter((detail) => detail.value !== undefined),
        );

        this.containerTokenData().data = containerDetails.tokens;
        this.tokenOptions.set(tokens.result.value.tokens);
        this.length = tokens.result.value.count;

        let user = {
          user_realm: '',
          user_name: '',
          user_resolver: '',
          user_id: '',
        };
        if (containerDetails['users'].length) {
          user = containerDetails['users'][0];
        }
        this.userData.set(
          containerUserDetailsKeyMap
            .map((detail) => ({
              keyMap: detail,
              value: user[detail.key as keyof typeof user],
              isEditing: signal(false),
            }))
            .filter((detail) => detail.value !== undefined),
        );
        this.userRealm = this.userData().find(
          (detail) => detail.keyMap.key === 'user_realm',
        )?.value;
        this.realmOptions.set(Object.keys(realms.result.value));
        this.selectedRealms.set(containerDetails.realms);
        this.states.set(containerDetails['states']);
        return new Observable<void>((observer) => {
          observer.next();
          observer.complete();
        });
      }),
      catchError((error) => {
        console.error('Failed to get container details.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to get container details. ' + message,
        );
        throw error;
      }),
    );
  }

  isEditableElement(key: string) {
    return key === 'description' || key === 'realms';
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

  saveUser() {
    this.containerService
      .assignUser(
        this.containerSerial(),
        this.selectedUsername(),
        this.userRealm,
      )
      .subscribe({
        next: () => {
          this.refreshContainerDetails.set(true);
        },
        error: (error) => {
          console.error('Failed to assign user.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to assign user. ' + message,
          );
        },
      });
  }

  unassignUser() {
    this.containerService
      .unassignUser(
        this.containerSerial(),
        this.userData().find((detail) => detail.keyMap.key === 'user_name')
          ?.value,
        this.userData().find((detail) => detail.keyMap.key === 'user_realm')
          ?.value,
      )
      .subscribe({
        next: () => {
          this.refreshContainerDetails.set(true);
        },
        error: (error) => {
          console.error('Failed to unassign user.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to unassign user. ' + message,
          );
        },
      });
  }

  onPageChanged(event: PageEvent): void {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.fetchTokenData();

    setTimeout(() => {
      this.tokenFilterInput.nativeElement.focus();
      this.tokenAutoTrigger.openPanel();
    }, 0);
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    if (this.showOnlyTokenNotInContainer()) {
      this.filterValue = this.filterValue + ' container_serial:';
    }
    this.pageIndex = 0;
    this.fetchTokenData();
  }

  addTokenToContainer(option: TokenOption) {
    this.containerService
      .addTokenToContainer(this.containerSerial(), option['serial'])
      .pipe(switchMap(() => this.showContainerDetail()))
      .subscribe({
        next: () => {
          this.showContainerDetail();
        },
        error: (error) => {
          console.error('Failed to add token to container.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to add token to container. ' + message,
          );
        },
      });
  }

  handleCancelAction(type: string) {
    switch (type) {
      case 'realms':
        this.selectedRealms.set([]);
        break;
      default:
        this.showContainerDetail().subscribe();
        break;
    }
  }

  private fetchTokenData() {
    this.tokenService
      .getTokenData(
        this.pageIndex + 1,
        this.pageSize,
        undefined,
        this.filterValue,
      )
      .subscribe({
        next: (response: any) => {
          this.tokenOptions.set(response.result.value.tokens);
          this.length = response.result.value.count;
        },
        error: (error) => {
          console.error('Failed to get token data.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to get token data. ' + message,
          );
        },
      });
  }

  private _filterUserOptions(value: string): string[] {
    const filterValue = value.toLowerCase();
    return this.userOptions().filter((option) =>
      option.toLowerCase().includes(filterValue),
    );
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
    this.containerService
      .setContainerRealm(this.containerSerial(), this.selectedRealms())
      .pipe(switchMap(() => this.showContainerDetail()))
      .subscribe({
        next: () => {
          this.showContainerDetail();
        },
        error: (error) => {
          console.error('Failed to save token realms.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to save token realms. ' + message,
          );
        },
      });
  }

  private saveDescription() {
    const description = this.containerDetailData().find(
      (detail) => detail.keyMap.key === 'description',
    )?.value;
    this.containerService
      .setContainerDescription(this.containerSerial(), description)
      .pipe(switchMap(() => this.showContainerDetail()))
      .subscribe({
        next: () => {
          this.showContainerDetail();
        },
        error: (error) => {
          console.error('Failed to save token description.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to save token description. ' + message,
          );
        },
      });
  }
}
