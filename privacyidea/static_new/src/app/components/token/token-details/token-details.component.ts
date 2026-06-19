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
  AfterViewInit,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  OnDestroy,
  OnInit,
  Renderer2,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatButton } from "@angular/material/button";
import { MatCell, MatColumnDef, MatRow, MatTable, MatTableModule } from "@angular/material/table";
import { Router, RouterLink } from "@angular/router";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { LostTokenComponent } from "./token-details-actions/lost-token/lost-token.component";
import { TokenRolloverComponent } from "./token-details-actions/token-rollover/token-rollover.component";
import {
  HotpMachineAssignDialogData,
  TokenHotpMachineAssignDialogComponent
} from "./token-machine-attach-dialog/token-hotp-machine-attach-dialog/token-hotp-machine-attach-dialog";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { ValidateService, ValidateServiceInterface } from "@services/validate/validate.service";
import { tokenTypes } from "@utils/token.utils";
import { lastValueFrom, switchMap } from "rxjs";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface, TokenTypeKey } from "@services/token/token.service";

import { NgClass, NgTemplateOutlet } from "@angular/common";
import { MatIconButton } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatListItem } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { DetailsHeaderComponent } from "@components/shared/details-shared/details-header/details-header.component";
import { AutofocusDirective } from "@components/shared/directives/app-autofocus.directive";
import { OverflowNavDirective } from "@components/shared/directives/overflow-nav/overflow-nav.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { Base64Service, Base64ServiceInterface } from "@services/base64/base64.service";
import { PolicyAction } from "@services/auth/policy-actions";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { MachineService, MachineServiceInterface } from "@services/machine/machine.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { TokenDetailsActionsComponent } from "./token-details-actions/token-details-actions.component";
import { TokenDetailsInfoComponent } from "./token-details-info/token-details-info.component";
import { TokenDetailsMachineComponent } from "./token-details-machine/token-details-machine.component";
import { TokenDetailsUserComponent } from "./token-details-user/token-details-user.component";
import {
  SshMachineAssignDialogData,
  TokenSshMachineAssignDialogComponent
} from "./token-machine-attach-dialog/token-ssh-machine-attach-dialog/token-ssh-machine-attach-dialog";

export const TIMESTAMP_INFO_KEYS = ["creation_date", "assignment_date", "last_auth"] as const;
export const USER_TIMESTAMP_INFO_KEYS = ["assignment_date"] as const;

type TokenDetailGroup = "identity" | "counters" | "assignment";

export const tokenDetailsKeyMap: { key: string; label: string; group: TokenDetailGroup }[] = [
  { key: "tokentype", label: $localize`Type`, group: "identity" },
  { key: "active", label: $localize`Status`, group: "identity" },
  { key: "rollout_state", label: $localize`Rollout State`, group: "identity" },
  { key: "failcount", label: $localize`Fail Count`, group: "identity" },
  { key: "creation_date", label: $localize`Created`, group: "identity" },
  { key: "last_auth", label: $localize`Last Authentication`, group: "identity" },
  { key: "maxfail", label: $localize`Max Count`, group: "counters" },
  { key: "otplen", label: $localize`OTP Length`, group: "counters" },
  { key: "count_window", label: $localize`Count Window`, group: "counters" },
  { key: "sync_window", label: $localize`Sync Window`, group: "counters" },
  { key: "count", label: $localize`Count`, group: "counters" },
  { key: "description", label: $localize`Description`, group: "assignment" },
  { key: "realms", label: $localize`Token Realms`, group: "assignment" },
  { key: "tokengroup", label: $localize`Token Groups`, group: "assignment" },
  { key: "container_serial", label: $localize`Container Serial`, group: "assignment" }
];

export const tokenDetailGroups: { id: TokenDetailGroup; label: string }[] = [
  { id: "identity", label: $localize`Status` },
  { id: "counters", label: $localize`Counters` },
  { id: "assignment", label: $localize`Assignments` }
];

function formatTokenTimestamp(value: string | undefined): string | undefined {
  if (value === undefined || value === "") return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export const tokenDetailsRightsMap = [
  { key: "maxfail", right: "set" },
  { key: "count_window", right: "set" },
  { key: "sync_window", right: "set" },
  { key: "description", right: "setdescription" },
  { key: "realms", right: "tokenrealms" },
  { key: "tokengroup", right: "tokengroups" },
  { key: "container_serial", right: "container_add_token" }
];

export const userDetailsKeyMap = [
  { key: "username", label: $localize`User` },
  { key: "user_realm", label: $localize`Realm` },
  { key: "assignment_date", label: $localize`Last Assigned` },
  { key: "resolver", label: $localize`Resolver` },
  { key: "user_id", label: $localize`User ID` }
];

export const infoDetailsKeyMap = [{ key: "info", label: $localize`Information` }];

@Component({
  imports: [
    MatCell,
    MatTableModule,
    MatColumnDef,
    MatIcon,
    MatListItem,
    MatRow,
    MatTable,
    NgClass,
    NgTemplateOutlet,
    MatInput,
    MatFormFieldModule,
    MatSelectModule,
    MatCheckbox,
    MatIconButton,
    TokenDetailsUserComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    EditButtonsComponent,
    CopyButtonComponent,
    MatButton,
    RouterLink,
    AutofocusDirective,
    ScrollToTopDirective,
    ClearableInputComponent,
    CopyButtonComponent,
    ClearableInputComponent,
    TokenDetailsMachineComponent,
    DetailsHeaderComponent,
    OverflowNavDirective
  ],
  templateUrl: "./token-details.component.html",
  styleUrls: ["./token-details.component.scss"]
})
export class TokenDetailsComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly renderer = inject(Renderer2);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly machineService: MachineServiceInterface = inject(MachineService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly validateService: ValidateServiceInterface = inject(ValidateService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  private readonly router = inject(Router);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected isLost = signal(false);
  protected readonly rolloverTokenTypes = computed(() =>
    tokenTypes.filter((t) => t.rollover === true).map((t) => t.key)
  );
  protected readonly tokenTypeKey = computed(() => this.tokenType() as TokenTypeKey);
  tokenIsActive = this.tokenService.tokenIsActive;
  tokenIsRevoked = this.tokenService.tokenIsRevoked;
  tokenSerial = this.tokenService.tokenSerial;
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  setPinValue = signal("");
  repeatPinValue = signal("");
  passkeyTestResult = signal<{
    kind: "success" | "warning";
    message: string;
    mismatch?: { serial: string; username: string; realm?: string };
  } | null>(null);
  isAttachedToMachine = computed<boolean>(() => {
    const tokenApplications = this.machineService.tokenApplications();
    if (!tokenApplications) return false;
    if (tokenApplications.length === 0) return false;
    return true;
  });
  tokenDetailResource = this.tokenService.tokenDetailResource;
  tokenDetails: WritableSignal<TokenDetails> = linkedSignal({
    source: () => (this.tokenDetailResource.hasValue() ? this.tokenDetailResource.value() : undefined),
    computation: (tokenDetailResource) => {
      const tokenDetail = tokenDetailResource?.result?.value?.tokens[0] as TokenDetails | undefined;
      return (
        tokenDetail ?? {
          active: false,
          container_serial: "",
          count: 0,
          count_window: 0,
          description: "",
          failcount: 0,
          id: 0,
          info: {},
          locked: false,
          maxfail: 0,
          otplen: 0,
          realms: [],
          resolver: "",
          revoked: false,
          rollout_state: "",
          serial: "",
          sync_window: 0,
          tokengroup: [],
          tokentype: "hotp",
          user_id: "",
          user_realm: "",
          username: ""
        }
      );
    }
  });
  tokenDetailData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return tokenDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return tokenDetailsKeyMap
        .map((detail) => {
          const fromInfo = (TIMESTAMP_INFO_KEYS as readonly string[]).includes(detail.key);
          const value = fromInfo
            ? formatTokenTimestamp(details.info?.[detail.key])
            : details[detail.key as keyof TokenDetails];
          return {
            keyMap: detail,
            value,
            isEditing: signal(false)
          };
        })
        .filter((detail) => detail.value !== undefined);
    }
  });
  infoData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return infoDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return infoDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: details[detail.key as keyof TokenDetails],
          isEditing: signal(false)
        }))
        .filter((detail) => detail.value !== undefined);
    }
  });
  userData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return userDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return userDetailsKeyMap
        .map((detail) => {
          const fromInfo = (USER_TIMESTAMP_INFO_KEYS as readonly string[]).includes(detail.key);
          const value = fromInfo
            ? formatTokenTimestamp(details.info?.[detail.key])
            : details[detail.key as keyof TokenDetails];
          return {
            keyMap: detail,
            value,
            isEditing: signal(false)
          };
        })
        .filter((detail) => detail.value !== undefined);
    }
  });
  tokenDetailDataByGroup = computed(() => {
    const data = this.tokenDetailData();
    const type = this.tokenDetails()?.tokentype;
    const hideCounters = type === "webauthn" || type === "passkey" || type === "push";
    return tokenDetailGroups
      .filter((g) => !(hideCounters && g.id === "counters"))
      .map((g) => ({
        id: g.id,
        label: g.label,
        rows: data.filter(
          (r) => (r.keyMap as { group?: string }).group === g.id && r.keyMap.key !== "description"
        )
      }));
  });
  descriptionRow = computed(
    () => this.tokenDetailData().find((r) => r.keyMap.key === "description") as EditableElement<string> | undefined
  );
  tokengroupOptions = signal<string[]>([]);
  selectedTokengroup = signal<string[]>([]);
  tokenType = linkedSignal({
    source: this.tokenDetails,
    computation: () => this.tokenDetails()?.tokentype ?? ""
  });
  userRealm = "";
  maxfail = 0;
  isAnyEditingOrRevoked = computed(() => {
    return (
      this.tokenDetailData().some((element) => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo() ||
      this.tokenIsRevoked()
    );
  });

  constructor() {
    effect(() => {
      if (!this.tokenDetails()) return;
      this.tokenIsActive.set(this.tokenDetails().active);
      this.tokenIsRevoked.set(this.tokenDetails().revoked);
      this.maxfail = this.tokenDetails().maxfail;
      this.realmService.selectedRealms.set(this.tokenDetails().realms);
      this.userRealm = (this.userData().find((detail) => detail.keyMap.key === "user_realm")?.value as string) || "";
      this.containerService.compatibleWithSelectedTokenType.set(this.tokenDetails().tokentype);
    });
  }

  @ViewChild(TokenDetailsUserComponent) userChild?: TokenDetailsUserComponent;
  @ViewChild(TokenDetailsInfoComponent) infoChild?: TokenDetailsInfoComponent;
  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;

  private stickyObserver?: IntersectionObserver;

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(
      () =>
        this.tokenDetailData().some((element) => element.isEditing()) || this.isEditingUser() || this.isEditingInfo()
    );
    this.pendingChangesService.registerValidChanges(() => true);
    this.pendingChangesService.registerSave(() => this.saveAllInlineEdits());
  }

  async saveAllInlineEdits(): Promise<boolean> {
    for (const row of this.tokenDetailData()) {
      if (row.isEditing()) {
        this.saveTokenEdit(row);
      }
    }
    if (this.isEditingUser()) {
      this.userChild?.saveUser();
    }
    if (this.isEditingInfo()) {
      const infoElement = this.infoData().find((d) => d.keyMap.key === "info");
      if (infoElement) {
        this.infoChild?.saveInfo(infoElement as unknown as EditableElement<Record<string, string>>);
      } else {
        this.isEditingInfo.set(false);
      }
    }
    return true;
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) return;

    this.stickyObserver = new IntersectionObserver(
      ([entry]) => {
        if (!entry.rootBounds) return;
        const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;
        if (shouldFloat) {
          this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
        } else {
          this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
        }
      },
      { root: this.scrollContainer.nativeElement, threshold: [0, 1] }
    );
    this.stickyObserver.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.stickyObserver?.disconnect();
  }

  resetFailCount(): void {
    this.tokenService.resetFailCount(this.tokenSerial()).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }

  toggleActive(): void {
    this.tokenService.toggleActive(this.tokenSerial(), this.tokenIsActive()).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }

  deleteToken(): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Delete Token`,
          items: [this.tokenSerial()],
          itemType: "token",
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.deleteToken(this.tokenSerial()).subscribe({
              next: () => {
                this.router.navigateByUrl(ROUTE_PATHS.TOKENS).then();
                this.tokenSerial.set("");
              }
            });
          }
        }
      });
  }

  revokeToken(): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Revoke Token`,
          items: [this.tokenSerial()],
          itemType: "token",
          confirmAction: { label: $localize`Revoke`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService
              .revokeToken(this.tokenSerial())
              .pipe(switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial())))
              .subscribe({
                next: () => {
                  this.tokenDetailResource.reload();
                }
              });
          }
        }
      });
  }

  testPasskey(): void {
    this.passkeyTestResult.set(null);
    const expectedHash = (this.tokenDetails()?.info as Record<string, string> | undefined)?.["credential_id_hash"];
    let usedCredentialId: string | null = null;
    this.validateService
      .authenticatePasskey({
        isTest: true,
        onCredentialId: (id) => (usedCredentialId = id)
      })
      .subscribe({
        next: async (checkResponse) => {
          if (!checkResponse.result?.value) {
            this.passkeyTestResult.set({ kind: "warning", message: $localize`No user found.` });
            return;
          }
          const username = checkResponse.detail?.username ?? $localize`Unknown User`;
          const authenticatedSerial = checkResponse.detail?.serial;
          const isAdmin = this.authService.role() === "admin";
          let mismatch = false;
          if (isAdmin && expectedHash && usedCredentialId) {
            const actualHash = await this.sha256HexFromBase64Url(usedCredentialId);
            mismatch = actualHash.toLowerCase() !== expectedHash.toLowerCase();
          }
          if (mismatch) {
            const matchedSerial = authenticatedSerial ?? "";
            this.passkeyTestResult.set({
              kind: "warning",
              message: $localize`You authenticated with a different passkey than the one shown on this page.`,
              mismatch: { serial: matchedSerial, username }
            });
            if (matchedSerial) {
              this.tokenService.getTokenDetails(matchedSerial).subscribe({
                next: (response) => {
                  const realm = response?.result?.value?.tokens?.[0]?.user_realm;
                  const current = this.passkeyTestResult();
                  if (current?.mismatch && current.mismatch.serial === matchedSerial && realm) {
                    this.passkeyTestResult.set({
                      ...current,
                      mismatch: { ...current.mismatch, realm }
                    });
                  }
                }
              });
            }
          } else {
            this.passkeyTestResult.set({
              kind: "success",
              message: $localize`Authentication successful. You would have been logged in as: ` + username
            });
          }
        }
      });
  }

  private async sha256HexFromBase64Url(base64Url: string): Promise<string> {
    const bytes = this.base64Service.webAuthnBase64DecToArr(base64Url);
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
    const digest = await crypto.subtle.digest("SHA-256", buffer);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  attachSshToMachineDialog(): void {
    const data: SshMachineAssignDialogData = {
      tokenSerial: this.tokenSerial(),
      tokenType: this.tokenType(),
      tokenDetails: this.tokenDetails()
    };
    this.dialogService
      .openDialog({ component: TokenSshMachineAssignDialogComponent, data: data })
      .afterClosed()
      .subscribe((request) => {
        if (!request) return;
        lastValueFrom(request).then(() => {
          this.machineService.tokenApplicationResource.reload();
        });
      });
  }

  attachHotpToMachineDialog(): void {
    const data: HotpMachineAssignDialogData = { tokenSerial: this.tokenSerial() };
    this.dialogService
      .openDialog({ component: TokenHotpMachineAssignDialogComponent, data: data })
      .afterClosed()
      .subscribe((request) => {
        if (request) {
          lastValueFrom(request).then(() => {
            this.machineService.tokenApplicationResource.reload();
          });
        }
      });
  }

  attachPasskeyToMachine(): void {
    this.machineService
      .postAssignMachineToToken({
        serial: this.tokenSerial(),
        application: "offline",
        machineid: 0,
        resolver: ""
      })
      .subscribe({
        next: () => {
          this.machineService.tokenApplicationResource.reload();
        },
        error: (error) => {
          console.error("Error during assignment request:", error);
        }
      });
  }

  removePasskeyFromMachine(): void {
    const mtid = this.machineService.tokenApplications()?.[0]?.id;
    this.machineService
      .deleteAssignMachineToToken({
        serial: this.tokenSerial(),
        application: "offline",
        mtid: `${mtid}`
      })
      .subscribe({
        next: () => {
          this.machineService.tokenApplicationResource.reload();
        },
        error: (error) => {
          console.error("Error during unassignment request:", error);
        }
      });
  }

  openLostTokenDialog(): void {
    this.dialogService.openDialog({
      component: LostTokenComponent,
      data: { isLost: this.isLost, tokenSerial: this.tokenSerial }
    });
  }

  rolloverToken(): void {
    const token = this.tokenDetails();
    if (!token) return;
    this.dialogService.openDialog({
      component: TokenRolloverComponent,
      data: { token: token }
    });
  }

  cancelTokenEdit(element: EditableElement) {
    this.resetEdit(element.keyMap.key);
    element.isEditing.set(!element.isEditing());
  }

  saveTokenEdit(element: EditableElement) {
    switch (element.keyMap.key) {
      case "container_serial":
        this.containerService.selectedContainerSerial.set(
          this.containerService.selectedContainerSerial()?.trim() ?? null
        );
        this.saveContainer();
        break;
      case "tokengroup":
        this.saveTokengroup(this.selectedTokengroup());
        break;
      case "realms":
        this.saveRealms();
        break;
      default:
        this.saveTokenDetail(element.keyMap.key, element.value);
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  toggleTokenEdit(element: EditableElement): void {
    switch (element.keyMap.key) {
      case "tokengroup":
        if (this.tokengroupOptions().length === 0) {
          this.tokenService.getTokengroups().subscribe({
            next: (response) => {
              const tokengroups = response.result?.value || {};
              this.tokengroupOptions.set(Object.keys(tokengroups));
              this.selectedTokengroup.set(
                (this.tokenDetailData().find((detail) => detail.keyMap.key === "tokengroup")?.value as string[]) ?? []
              );
            }
          });
        }
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  saveTokenDetail(key: string, value: unknown): void {
    this.tokenService.saveTokenDetail(this.tokenSerial(), key, value).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }

  saveContainer() {
    const selectedContainer = this.containerService.selectedContainerSerial();
    if (selectedContainer) {
      this.containerService.addToken(this.tokenSerial(), selectedContainer).subscribe({
        next: () => {
          this.tokenDetailResource.reload();
        }
      });
    }
  }

  removeFromContainer() {
    const containerSerial = this.tokenDetails().container_serial;

    if (!containerSerial) {
      return;
    }

    this.containerService.removeToken(this.tokenSerial(), containerSerial).subscribe({
      next: () => {
        this.containerService.selectedContainerSerial.set("");
        this.tokenDetailResource.reload();
      }
    });
  }

  isEditableElement(key: string) {
    const rightEntry = tokenDetailsRightsMap.find((entry) => entry.key === key);
    return !!(rightEntry && this.authService.actionAllowed(rightEntry.right as PolicyAction));
  }

  isNumberElement(key: string) {
    return key === "maxfail" || key === "count_window" || key === "sync_window";
  }

  openSshMachineAssignDialog() {
    const data: SshMachineAssignDialogData = {
      tokenSerial: this.tokenSerial(),
      tokenDetails: this.tokenDetails(),
      tokenType: this.tokenType()
    };

    this.dialogService.openDialog({ component: TokenSshMachineAssignDialogComponent, data: data });
  }

  protected showTokenAuditLog() {
    this.auditService.auditFilter.set(new FilterValue({ value: `serial: ${this.tokenSerial()}` }));
  }

  private resetEdit(type: string): void {
    switch (type) {
      case "container_serial":
        this.containerService.selectedContainerSerial.set("");
        break;
      case "tokengroup":
        this.selectedTokengroup.set(
          (this.tokenDetailData().find((detail) => detail.keyMap.key === "tokengroup")?.value as string[]) ?? []
        );
        break;
      case "realms":
        this.realmService.selectedRealms.set(
          (this.tokenDetailData().find((detail) => detail.keyMap.key === "realms")?.value as string[]) ?? []
        );
        break;
      default:
        this.tokenDetailResource.reload();
        break;
    }
  }

  private saveRealms() {
    this.tokenService.setTokenRealm(this.tokenSerial(), this.realmService.selectedRealms()).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }

  private saveTokengroup(value: string[]) {
    this.tokenService.setTokengroup(this.tokenSerial(), value).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }
}
