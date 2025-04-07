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
import { forkJoin, Observable, switchMap } from 'rxjs';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatListItem } from '@angular/material/list';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { EditButtonsComponent } from '../../shared/edit-buttons/edit-buttons.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { RealmService } from '../../../services/realm/realm.service';
import { catchError } from 'rxjs/operators';
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
import { NotificationService } from '../../../services/notification/notification.service';
import { TokenSelectedContent } from '../token.component';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { UserService } from '../../../services/user/user.service';

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
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
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
    protected tokenService: TokenService,
    private notificationService: NotificationService,
    protected userService: UserService,
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
        const userRealm = this.userData().find(
          (detail) => detail.keyMap.key === 'user_realm',
        )?.value;
        this.userService.selectedUserRealm.set(userRealm || '');
        this.userRealm = userRealm || '';
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
    this.showContainerDetail().subscribe();
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
          this.userService.setDefaultRealm(this.realmService);
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
          this.userService.resetUserSelection();
          this.isEditingUser.update((b) => !b);
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
