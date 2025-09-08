/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import {
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import {
  ContainerDetailData,
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { EditableElement, EditButtonsComponent } from "../../shared/edit-buttons/edit-buttons.component";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatCell, MatColumnDef, MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { OverflowService, OverflowServiceInterface } from "../../../services/overflow/overflow.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";

import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { ContainerDetailsInfoComponent } from "./container-details-info/container-details-info.component";
import { ContainerDetailsTokenTableComponent } from "./container-details-token-table/container-details-token-table.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { FilterValue } from "../../../core/models/filter_value";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDivider } from "@angular/material/divider";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { NgClass } from "@angular/common";
import { ROUTE_PATHS } from "../../../route_paths";
import { Router } from "@angular/router";
import { infoDetailsKeyMap } from "../token-details/token-details.component";

export const containerDetailsKeyMap = [
  { key: "type", label: "Type" },
  { key: "states", label: "Status" },
  { key: "description", label: "Description" },
  { key: "realms", label: "Realms" }
];

const containerUserDetailsKeyMap = [
  { key: "user_realm", label: "User Realm" },
  { key: "user_name", label: "User" },
  { key: "user_resolver", label: "Resolver" },
  { key: "user_id", label: "User ID" }
];

const allowedTokenTypesMap = new Map<string, string | string[]>([
  ["yubikey", ["certificate", "hotp", "passkey", "webauthn", "yubico", "yubikey"]],
  ["smartphone", ["daypassword", "hotp", "push", "sms", "totp"]],
  ["generic", "all"]
]);

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
    MatPaginator,
    MatDivider,
    MatCheckbox,
    CopyButtonComponent,
    ClearableInputComponent
  ],
  templateUrl: "./container-details.component.html",
  styleUrls: ["./container-details.component.scss"]
})
export class ContainerDetailsComponent {
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
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
    source: this.tokenResource.value,
    computation: (tokenResource, previous) => {
      if (tokenResource && tokenResource.result?.value) {
        return new MatTableDataSource(tokenResource.result?.value.tokens);
      }
      return previous?.value ?? new MatTableDataSource();
    }
  });
  total: WritableSignal<number> = linkedSignal({
    source: this.tokenResource.value,
    computation: (tokenResource, previous) => {
      if (tokenResource && tokenResource.result?.value) {
        return tokenResource.result?.value.count;
      }
      return previous?.value ?? 0;
    }
  });

  containerDetailResource = this.containerService.containerDetailResource;
  containerDetails = linkedSignal({
    source: this.containerDetailResource.value,
    computation: (containerDetailResourceValue) => {
      const value = containerDetailResourceValue?.result?.value;
      if (value && value.containers.length > 0) {
        return value.containers[0];
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
          value: (containerDetails as any)[detail.key],
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
          value: (containerDetails as any)[detail.key],
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
    effect(() => {
      this.showOnlyTokenNotInContainer();
      if (this.filterHTMLInputElement) {
        this.filterHTMLInputElement.nativeElement.focus();
      }
    });
    effect(() => {
      const res = this.containerDetailResource.value();
      if (res && res?.result?.value?.containers.length === 0) {
        setTimeout(() => {
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS);
        });
      }
    });
  }

  _addTypeListToFilter(currentFilter: FilterValue): FilterValue {
    const containerDetails = this.containerDetails();
    const containerType = containerDetails?.type;
    const allowedTokenTypes = allowedTokenTypesMap.get(containerType);
    const _currentFilter = currentFilter.copyWith();
    if (
      !allowedTokenTypes ||
      allowedTokenTypes === "all" ||
      !Array.isArray(allowedTokenTypes) ||
      allowedTokenTypes.length === 0
    ) {
      _currentFilter.removeKey("type");
      _currentFilter.removeKey("type_list");
      return _currentFilter;
    }
    if (allowedTokenTypes.length === 1) {
      _currentFilter.addEntry("type", allowedTokenTypes[0]);
      _currentFilter.removeKey("type_list");
    } else {
      _currentFilter.addEntry("type_list", allowedTokenTypes.join(","));
      _currentFilter.removeKey("type");
    }
    return _currentFilter;
  }

  isEditableElement(key: string) {
    if (key === "description" && this.authService.actionAllowed("container_description")) {
      return true;
    } else if (key === "realms" && this.authService.actionAllowed("container_realms")) {
      return true;
    }
    return false;
  }

  cancelContainerEdit(element: EditableElement) {
    switch (element.keyMap.key) {
      case "realms":
        this.selectedRealms.set([]);
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
}
