/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { NgClass } from "@angular/common";
import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  WritableSignal,
  computed,
  effect,
  inject,
  linkedSignal,
  signal
} from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { MatFormField, MatSelectModule } from "@angular/material/select";
import { MatCell, MatColumnDef, MatTableDataSource, MatTableModule } from "@angular/material/table";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContainerDetailsActionsComponent } from "@components/container/container-details/container-details-actions/container-details-actions.component";
import { ContainerDetailsInfoComponent } from "@components/container/container-details/container-details-info/container-details-info.component";
import { ContainerDetailsTokenActionsComponent } from "@components/container/container-details/container-details-token-actions/container-details-token-actions.component";
import { ContainerDetailsTokenTableComponent } from "@components/container/container-details/container-details-token-table/container-details-token-table.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ContainerAddTokenComponent } from "@components/shared/container-add-token/container-add-token.component";
import { DetailsHeaderComponent } from "@components/shared/details-shared/details-header/details-header.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { EditButtonsComponent, EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";
import { infoDetailsKeyMap } from "@components/token/token-details/token-details.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  CONTAINER_STATE_OPTIONS,
  ContainerDetailData,
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";

export const containerDetailsKeyMap = [
  { key: "type", label: "Type" },
  { key: "states", label: "Status" },
  { key: "description", label: "Description" },
  { key: "realms", label: "Realms" },
  { key: "template", label: "Template" }
];

const containerUserDetailsKeyMap = [
  { key: "user_realm", label: "User Realm" },
  { key: "user_name", label: "User" },
  { key: "user_resolver", label: "Resolver" },
  { key: "user_id", label: "User ID" }
];

interface TokenOption {
  serial: string;
  tokentype: string;
  active: boolean;
  username: string;
}

@Component({
  selector: "app-container-details",
  standalone: true,
  imports: [
    NgClass,
    MatTableModule,
    MatCell,
    MatColumnDef,
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
    MatDivider,
    ClearableInputComponent,
    ContainerDetailsActionsComponent,
    ScrollToTopDirective,
    ContainerDetailsTokenActionsComponent,
    DetailsHeaderComponent,
    ContainerAddTokenComponent
  ],
  templateUrl: "./container-details.component.html",
  styleUrls: ["./container-details.component.scss"]
})
export class ContainerDetailsComponent implements OnInit, OnDestroy {
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private previousPageSize = 10;
  private router = inject(Router);
  states = this.containerService.states;
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  tokenSerial = this.tokenService.tokenSerial;
  containerSerial = this.containerService.containerSerial;
  showOnlyTokenNotInContainer = this.tokenService.showOnlyTokenNotInContainer;
  tokenResource = this.tokenService.tokenResource;
  pageIndex = this.tokenService.pageIndex;
  pageSize = this.tokenService.pageSize;
  tokenDataSource: WritableSignal<MatTableDataSource<TokenDetails>> = linkedSignal({
    source: this.tokenService.tokenResourceValue,
    computation: (tokenResourceValue, previous) => {
      if (tokenResourceValue) {
        return new MatTableDataSource(tokenResourceValue.tokens);
      }
      return previous?.value ?? new MatTableDataSource();
    }
  });
  total: WritableSignal<number> = linkedSignal({
    source: this.tokenService.tokenResourceValue,
    computation: (tokenResourceValue, previous) => {
      if (tokenResourceValue) {
        return tokenResourceValue.count;
      }
      return previous?.value ?? 0;
    }
  });
  containerDetailResource = this.containerService.containerDetailsResource;
  containerDetails: WritableSignal<ContainerDetailData> = linkedSignal({
    source: this.containerDetailResource.value,
    computation: (containerDetailResourceValue, previous) => {
      const value = containerDetailResourceValue?.result?.value;
      if (value && value.containers.length > 0) {
        return value.containers[0];
      } else if (previous?.value) {
        return previous.value;
      }

      const emptyContainerDetails: ContainerDetailData = {
        type: "",
        tokens: [],
        states: [],
        description: "",
        select: "",
        serial: "",
        users: [
          {
            user_realm: "",
            user_name: "",
            user_resolver: "",
            user_id: ""
          }
        ],
        user_realm: "",
        realms: []
      };
      return emptyContainerDetails;
    }
  });
  containerType = computed(() => {
    return this.containerDetails()?.type ?? "";
  });
  containerDetailData = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => {
      if (!containerDetails) {
        return containerDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return containerDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: containerDetails[detail.key as keyof ContainerDetailData],
          isEditing: signal(false)
        }))
        .filter((detail) => detail.value !== undefined);
    }
  });
  infoData = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => {
      if (containerDetails.serial === "") {
        return infoDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return infoDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: containerDetails[detail.key as keyof ContainerDetailData],
          isEditing: signal(false)
        }))
        .filter((detail) => detail.value !== undefined);
    }
  });
  containerTokenData: WritableSignal<MatTableDataSource<ContainerDetailToken, MatPaginator>> = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails, previous) => {
      if (!containerDetails) {
        return previous?.value ?? new MatTableDataSource<ContainerDetailToken, MatPaginator>([]);
      }
      return new MatTableDataSource<ContainerDetailToken, MatPaginator>(containerDetails.tokens ?? []);
    }
  });
  selectedRealms = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => containerDetails?.realms || []
  });

  selectedStates = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => containerDetails?.states || []
  });

  readonly containerStateOptions = CONTAINER_STATE_OPTIONS;
  rawUserData = linkedSignal({
    source: this.containerDetails,
    computation: (containerDetails) => {
      if (!containerDetails || !Array.isArray(containerDetails.users) || containerDetails.users.length === 0) {
        return {
          user_realm: "",
          user_name: "",
          user_resolver: "",
          user_id: ""
        };
      }
      return containerDetails.users[0];
    }
  });
  userData = linkedSignal({
    source: this.rawUserData,
    computation: (user) => {
      return containerUserDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: user[detail.key as keyof typeof user],
          isEditing: signal(false)
        }))
        .filter((detail) => detail.value !== undefined);
    }
  });
  userRealm = linkedSignal({
    source: this.rawUserData,
    computation: (user) => user.user_realm || ""
  });
  isAnyEditing = computed(() => {
    return (
      this.containerDetailData().some((element) => element.isEditing()) || this.isEditingUser() || this.isEditingInfo()
    );
  });
  @ViewChild("filterHTMLInputElement")
  filterHTMLInputElement!: ElementRef<HTMLInputElement>;
  @ViewChild("tokenAutoTrigger", { read: MatAutocompleteTrigger })
  tokenAutoTrigger!: MatAutocompleteTrigger;

  constructor() {
    this.previousPageSize = this.tokenService.pageSize();
    this.tokenService.pageSize.set(5);

    effect(() => {
      this.showOnlyTokenNotInContainer();
      // do not focus if showOnlyTokenNotInContainer is deselected to ensure the hint is visible
      if (this.filterHTMLInputElement && this.showOnlyTokenNotInContainer()) {
        this.filterHTMLInputElement.nativeElement.focus();
      }
    });
    effect(() => {
      if (!this.containerDetailResource.hasValue()) return;
      const res = this.containerDetailResource.value();
      if (res && res?.result?.value?.containers.length === 0) {
        setTimeout(() => {
          this.router.navigateByUrl(ROUTE_PATHS.CONTAINERS);
        });
      }
    });
  }

  isEditableElement(key: string) {
    if (key === "description" && this.authService.actionAllowed("container_description")) {
      return true;
    } else if (key === "realms" && this.authService.actionAllowed("container_realms")) {
      return true;
    } else if (key === "states" && this.authService.actionAllowed("container_state")) {
      return true;
    }
    return false;
  }

  cancelContainerEdit(element: EditableElement) {
    switch (element.keyMap.key) {
      case "realms":
        this.selectedRealms.set([]);
        break;
      case "states":
        this.selectedStates.set(this.containerDetails()?.states || []);
        break;
      case "user_name":
        this.isEditingUser.update((b) => !b);
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  saveContainerEdit(element: EditableElement) {
    switch (element.keyMap.key) {
      case "realms":
        this.saveRealms();
        break;
      case "description":
        this.saveDescription();
        break;
      case "states":
        if (!this.saveStates()) {
          return;
        }
        break;
      case "user_name":
        this.saveUser();
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  toggleContainerEdit(element: EditableElement) {
    switch (element.keyMap.key) {
      case "user_name":
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
        username: this.userService.selectionUsernameFilter(),
        userRealm: this.userService.selectedUserRealm()
      })
      .subscribe({
        next: () => {
          this.userService.selectionFilter.set("");
          this.userService.selectedUserRealm.set("");
          this.isEditingUser.update((b) => !b);
          this.containerDetailResource.reload();
        }
      });
  }

  unassignUser() {
    const userName = this.userData().find((d) => d.keyMap.key === "user_name")?.value;
    const userRealm = this.userData().find((d) => d.keyMap.key === "user_realm")?.value;
    this.containerService.unassignUser(this.containerSerial(), userName ?? "", userRealm ?? "").subscribe({
      next: () => {
        this.containerDetailResource.reload();
      }
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

  addTokenToContainer(option: TokenOption) {
    this.containerService.addTokenToContainer(this.containerSerial(), option["serial"]).subscribe({
      next: () => {
        this.containerDetailResource.reload();
        this.tokenService.tokenResource.reload();
      }
    });
  }

  onStatesChange(newStates: string[]) {
    if (newStates.includes("active") && newStates.includes("disabled")) {
      const prev = this.selectedStates();
      const toRemove = prev.includes("active") ? "active" : "disabled";
      this.selectedStates.set(newStates.filter((s) => s !== toRemove));
    } else {
      this.selectedStates.set(newStates);
    }
  }

  saveStates(): boolean {
    if (this.selectedStates().length === 0) {
      this.notificationService.error("At least one state must be selected.");
      return false;
    }
    this.containerService.setStates(this.containerSerial(), this.selectedStates()).subscribe({
      next: () => {
        this.containerDetailResource.reload();
      }
    });
    return true;
  }

  saveRealms() {
    this.containerService.setContainerRealm(this.containerSerial(), this.selectedRealms()).subscribe({
      next: () => {
        this.containerDetailResource.reload();
      }
    });
  }

  saveDescription() {
    const description = this.containerDetailData().find((detail) => detail.keyMap.key === "description")?.value;
    this.containerService.setContainerDescription(this.containerSerial(), description).subscribe({
      next: () => {
        this.containerDetailResource.reload();
      }
    });
  }

  @ViewChild(ContainerDetailsInfoComponent) infoChild?: ContainerDetailsInfoComponent;

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(() => this.isAnyEditing());
    this.pendingChangesService.registerValidChanges(() => true);
    this.pendingChangesService.registerSave(() => this.saveAllInlineEdits());
  }

  async saveAllInlineEdits(): Promise<boolean> {
    for (const row of this.containerDetailData()) {
      if (row.isEditing()) {
        this.saveContainerEdit(row);
      }
    }
    if (this.isEditingUser()) {
      this.saveUser();
    }
    if (this.isEditingInfo()) {
      const infoElement = this.infoData().find((d) => d.keyMap.key === "info");
      if (infoElement) {
        this.infoChild?.saveInfo(infoElement);
      } else {
        this.isEditingInfo.set(false);
      }
    }
    return true;
  }

  ngOnDestroy(): void {
    this.tokenService.pageSize.set(this.previousPageSize);
    this.pendingChangesService.clearAllRegistrations();
  }

  protected showContainerAuditLog() {
    this.auditService.auditFilter.set(new FilterValue({ value: `container_serial: ${this.containerSerial()}` }));
  }
}
