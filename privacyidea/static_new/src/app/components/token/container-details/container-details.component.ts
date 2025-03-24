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
import { OverflowService } from '../../../services/overflow/overflow.service';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { ContainerService } from '../../../services/container/container.service';
import {
  distinctUntilChanged,
  forkJoin,
  from,
  Observable,
  switchMap,
} from 'rxjs';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatListItem } from '@angular/material/list';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { EditButtonsComponent } from '../../shared/edit-buttons/edit-buttons.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { RealmService } from '../../../services/realm/realm.service';
import { catchError, map } from 'rxjs/operators';
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
import { TokenSelectedContent } from '../token.component';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';

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
  styleUrl: './container-details.component.scss',
})
export class ContainerDetailsComponent {
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() selectedUsername = signal<string>('');
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  selectedUserRealm = signal<string>('');
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
  length = signal(0);
  filterValue = signal('');
  pageIndex = linkedSignal({
    source: this.showOnlyTokenNotInContainer,
    computation: () => 0,
  });
  pageSize = signal(10);
  fetchedUsernames = toSignal(
    toObservable(this.selectedUserRealm).pipe(
      distinctUntilChanged(),
      switchMap((realm) => {
        if (!realm) {
          return from<string[]>([]);
        }
        return this.userService
          .getUsers(realm)
          .pipe(
            map((result: any) =>
              result.value.map((user: any) => user.username),
            ),
          );
      }),
    ),
    { initialValue: [] },
  );
  computedFilterValue = linkedSignal({
    source: this.showOnlyTokenNotInContainer,
    computation: (showOnlyTokenNotInContainer) => {
      if (showOnlyTokenNotInContainer) {
        return this.filterValue() + ' container_serial:';
      } else {
        return this.filterValue().replace(/container_serial:\S*/g, '');
      }
    },
  });
  userOptions = computed(() => this.fetchedUsernames());
  filteredUserOptions = computed(() => {
    const filterValue = (this.selectedUsername() || '').toLowerCase();
    return this.userOptions().filter((option: any) =>
      option.toLowerCase().includes(filterValue),
    );
  });
  isAnyEditing = computed(() => {
    const detailData = this.containerDetailData();

    return (
      detailData.some((element) => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo()
    );
  });
  pageSizeOptions = [10];
  userRealm = '';
  @ViewChild('tokenFilterInput')
  tokenFilterInput!: ElementRef<HTMLInputElement>;
  @ViewChild('tokenAutoTrigger', { read: MatAutocompleteTrigger })
  tokenAutoTrigger!: MatAutocompleteTrigger;
  @ViewChild(MatPaginator) paginator!: MatPaginator;

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
      this.showOnlyTokenNotInContainer();
      this.fetchTokenData();
      if (this.tokenFilterInput) {
        this.tokenFilterInput.nativeElement.focus();
      }
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
        this.paginator.pageIndex + 1,
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
        this.selectedUserRealm.set(
          this.userData().find((detail) => detail.keyMap.key === 'user_realm')
            ?.value,
        );
        this.userRealm = this.selectedUserRealm();
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
        if (
          action === 'edit' &&
          this.isEditingUser() &&
          this.selectedUserRealm() === ''
        ) {
          this.realmService.getDefaultRealm().subscribe({
            next: (realm: any) => {
              this.selectedUserRealm.set(realm);
            },
          });
        }
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
        this.selectedUserRealm(),
      )
      .subscribe({
        next: () => {
          this.refreshContainerDetails.set(true);
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
      });
  }

  onPageChanged(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);

    setTimeout(() => {
      this.tokenFilterInput.nativeElement.focus();
      this.tokenAutoTrigger.openPanel();
    }, 0);
  }

  handleFilterInput(event: Event) {
    this.filterValue.set((event.target as HTMLInputElement).value.trim());
    if (this.showOnlyTokenNotInContainer()) {
      this.filterValue.set(this.filterValue() + ' container_serial:');
    }
    this.pageIndex.set(0);
    this.paginator.pageIndex = this.pageIndex();
  }

  addTokenToContainer(option: TokenOption) {
    this.containerService
      .addTokenToContainer(this.containerSerial(), option['serial'])
      .pipe(switchMap(() => this.showContainerDetail()))
      .subscribe({
        next: () => {
          this.showContainerDetail();
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
        this.pageIndex() + 1,
        this.pageSize(),
        undefined,
        this.computedFilterValue(),
      )
      .subscribe({
        next: (response: any) => {
          this.tokenOptions.set(response.result.value.tokens);
          this.length = response.result.value.count;
        },
      });
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
      });
  }
}
