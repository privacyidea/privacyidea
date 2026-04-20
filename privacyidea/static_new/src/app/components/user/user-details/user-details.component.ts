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
import {
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  Signal,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { BreakpointObserver } from "@angular/cdk/layout";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { ROUTE_PATHS } from "../../../route_paths";
import { MatButtonModule } from "@angular/material/button";
import { UserDetailsTokenTableComponent } from "./user-details-token-table/user-details-token-table.component";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { MatIcon } from "@angular/material/icon";
import { TokenDetails, TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { MatTableDataSource } from "@angular/material/table";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { UserDetailsContainerTableComponent } from "./user-details-container-table/user-details-container-table.component";
import { UserDetailsPinDialogComponent } from "./user-details-pin-dialog/user-details-pin-dialog.component";
import { filter, map } from "rxjs";
import { FormsModule } from "@angular/forms";
import { MatSelectModule } from "@angular/material/select";
import { FilterValue } from "../../../core/models/filter_value/filter_value";
import { AuditService, AuditServiceInterface } from "../../../services/audit/audit.service";
import { MatTooltip } from "@angular/material/tooltip";
import { Router, RouterLink } from "@angular/router";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { EditUserDialogComponent } from "@components/user/edit-user-dialog/edit-user-dialog.component";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";

@Component({
  selector: "app-user-details",
  imports: [
    ScrollToTopDirective,
    MatButtonModule,
    UserDetailsTokenTableComponent,
    ClearableInputComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatFormField,
    MatIcon,
    MatInput,
    MatLabel,
    MatOption,
    MatFormField,
    NgClass,
    MatPaginator,
    UserDetailsContainerTableComponent,
    FormsModule,
    MatSelectModule,
    MatTooltip,
    RouterLink,
    CopyButtonComponent
  ],
  templateUrl: "./user-details.component.html",
  styleUrl: "./user-details.component.scss"
})
export class UserDetailsComponent {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private router = inject(Router);
  private breakpointObserver = inject(BreakpointObserver);

  private isSmall = toSignal(this.breakpointObserver.observe("(max-width: 1000px)").pipe(map((r) => r.matches)));
  private isMedium = toSignal(this.breakpointObserver.observe("(max-width: 1240px)").pipe(map((r) => r.matches)));

  colCount = computed(() => {
    if (this.isSmall()) return 1;
    if (this.isMedium()) return 2;
    return 3;
  });

  customColCount = computed(() => {
    if (this.isSmall()) return 1;
    return 2;
  });

  readonly labels: Record<string, string> = {
    username: $localize`Username`,
    givenname: $localize`Given name`,
    surname: $localize`Surname`,
    email: $localize`Email`,
    phone: $localize`Phone`,
    mobile: $localize`Mobile`,
    description: $localize`Description`,
    userid: $localize`User ID`,
    resolver: $localize`Resolver`
  };
  readonly excludedKeys = new Set(["editable"]);
  customAttributeKeys: Signal<Set<string>> = computed(() => {
    const attributeKeys = Object.entries(this.userService.userAttributesList()).map(([_, attribute]) => attribute.key);
    return new Set(attributeKeys);
  });

  userData = this.userService.user;
  tokenResource = this.tokenService.tokenResource;
  pageIndex = this.tokenService.pageIndex;
  pageSize = this.tokenService.pageSize;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  total: WritableSignal<number> = linkedSignal({
    source: this.tokenService.tokenResourceValue,
    computation: (tokenResourceValue, previous) => {
      if (tokenResourceValue) {
        return tokenResourceValue.count;
      }
      return previous?.value ?? 0;
    }
  });

  @ViewChild("filterHTMLInputElement")
  filterHTMLInputElement!: ElementRef<HTMLInputElement>;

  @ViewChild("tokenAutoTrigger", { read: MatAutocompleteTrigger })
  tokenAutoTrigger!: MatAutocompleteTrigger;

  tokenDataSource: WritableSignal<MatTableDataSource<TokenDetails>> = linkedSignal({
    source: this.tokenService.tokenResourceValue,
    computation: (tokenResourceValue, previous) => {
      if (tokenResourceValue) {
        return new MatTableDataSource(tokenResourceValue.tokens);
      }
      return previous?.value ?? new MatTableDataSource();
    }
  });

  attributeSetMap = this.userService.attributeSetMap;
  deletableAttributes = this.userService.deletableAttributes;
  keyOptions = this.userService.keyOptions;
  hasWildcardKey = this.userService.hasWildcardKey;
  addKeyInput = signal<string>("");
  addValueInput = signal<string>("");
  selectedKey = signal<string | null>(null);
  selectedValue = signal<string | null>(null);
  keyMode = signal<"select" | "input">("select");
  valueOptions = computed<string[]>(() => {
    const map = this.attributeSetMap();
    const mode = this.keyMode();
    const key = mode === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "");
    if (key && map[key]) return map[key];
    if (map["*"]) return map["*"];
    return [];
  });
  isValueInput = computed<boolean>(() => {
    const opts = this.valueOptions();
    if (opts.includes("*")) return true;
    return opts.length === 0;
  });
  canAddAttribute = computed<boolean>(() => {
    const key = this.keyMode() === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "").trim();
    const value = this.isValueInput() ? this.addValueInput().trim() : (this.selectedValue() ?? "").trim();
    return key.length > 0 && value.length > 0;
  });

  constructor() {
    effect(() => {
      const hasWildcard = this.hasWildcardKey();
      const hasFixedKeys = this.keyOptions().length > 0;
      if (hasWildcard && !hasFixedKeys) {
        this.keyMode.set("input");
      } else {
        this.keyMode.set("select");
      }
    });
  }

  detailsEntries = computed(() =>
    Object.entries(this.userData() ?? {})
      .filter(([key]) => !this.excludedKeys.has(key) && !this.customAttributeKeys().has(key))
      .map(([key, value]) => ({
        key,
        label: this.labels[key] ?? key,
        value: value ?? "-"
      }))
  );

  detailsColumns = computed(() => {
    const entries = this.detailsEntries();
    const colCount = this.colCount();
    const perCol = Math.ceil(entries.length / colCount);
    return Array.from({ length: colCount }, (_, i) => entries.slice(i * perCol, (i + 1) * perCol));
  });

  customAttributeColumns = computed(() => {
    const attributes = this.userService.userAttributesList();
    const colCount = this.customColCount();
    const perCol = Math.ceil(attributes.length / colCount);
    return Array.from({ length: colCount }, (_, i) => attributes.slice(i * perCol, (i + 1) * perCol));
  });

  switchToCustomKey() {
    this.keyMode.set("input");
    this.selectedKey.set(null);
  }

  switchToSelectKey() {
    this.keyMode.set("select");
    this.addKeyInput.set("");
  }

  addCustomAttribute() {
    const key = this.keyMode() === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "").trim();
    const value = this.isValueInput() ? this.addValueInput().trim() : (this.selectedValue() ?? "").trim();

    if (!key || !value) return;

    this.userService.setUserAttribute(key, value).subscribe({
      next: () => {
        this.userService.userAttributesResource.reload();
        this.addKeyInput.set("");
        this.addValueInput.set("");
        this.selectedKey.set(null);
        this.selectedValue.set(null);
      }
    });
  }

  deleteCustomAttribute(key: string) {
    this.userService.deleteUserAttribute(key).subscribe({
      next: () => this.userService.userAttributesResource.reload()
    });
  }

  assignUserToToken(option: TokenDetails) {
    this.dialogService
      .openDialog({ component: UserDetailsPinDialogComponent })
      .afterClosed()
      .pipe(filter((pin): pin is string => pin != null))
      .subscribe((pin: string) => {
        this.tokenService
          .assignUser({
            tokenSerial: option["serial"],
            username: this.userService.detailsUsername(),
            realm: this.userService.selectedUserRealm(),
            pin: pin
          })
          .subscribe({
            next: () => {
              this.tokenService.userTokenResource.reload();
              this.tokenService.tokenResource.reload();
            }
          });
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

  showUserAuditLog() {
    this.auditService.auditFilter.set(new FilterValue({ value: `user: ${this.userService.detailsUsername()}` }));
  }

  editUser() {
    this.dialogService.openDialog({
      component: EditUserDialogComponent,
      data: this.userData()
    });
  }

  deleteUser() {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Delete User",
          items: [this.userData().username],
          itemType: "user",
          confirmAction: { label: "Delete", value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.userService.deleteUser(this.userData().resolver, this.userData().username).subscribe({
              next: (success) => {
                if (success) {
                  this.router.navigateByUrl(ROUTE_PATHS.USERS).then();
                  this.userService.usersResource.reload();
                }
              }
            });
          }
        }
      });
  }

  protected readonly Array = Array;
}
