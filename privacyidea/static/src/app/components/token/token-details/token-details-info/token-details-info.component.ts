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
import { Component, computed, inject, Input, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import {
  INFO_KEY_EXISTS,
  InfoEntry,
  infoEntryRules
} from "@components/shared/details-shared/field-editing/info-entry.rules";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  isTokenInfoKeyWritable,
  TokenService,
  TokenServiceInterface
} from "@services/token/token.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";
import { Observable, switchMap } from "rxjs";
import { BLOB_INFO_KEYS, TIMESTAMP_INFO_KEYS } from "../token-details.constants";

@Component({
  selector: "app-token-details-info",
  standalone: true,
  imports: [
    MatFormFieldModule,
    MatInput,
    FormField,
    MatIconButton,
    MatIcon,
    MatDivider,
    EditButtonsComponent,
    DetailsCardComponent
  ],
  templateUrl: "./token-details-info.component.html",
  styleUrl: "./token-details-info.component.scss"
})
export class TokenDetailsInfoComponent {
  protected readonly Object = Object;
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  protected readonly INFO_KEY_EXISTS = INFO_KEY_EXISTS;
  protected readonly hiddenInfoKeys: readonly string[] = [...TIMESTAMP_INFO_KEYS, ...BLOB_INFO_KEYS];
  private tokenService: TokenServiceInterface = inject(TokenService);
  tokenSerial = this.tokenService.tokenSerial;
  @Input() infoData!: WritableSignal<EditableElement[]>;
  @Input() detailData!: WritableSignal<EditableElement[]>;
  @Input() isAnyEditingOrRevoked!: Signal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  /** Info entries the token maintains itself, see TokenDetails.readonly_info_keys */
  @Input() readonlyInfoKeys: Signal<string[]> = signal<string[]>([]);
  /** Info entries that may not be removed, see TokenDetails.undeletable_info_keys */
  @Input() undeletableInfoKeys: Signal<string[]> = signal<string[]>([]);
  /** Info entries that have their own endpoint, see TokenDetails.settable_info_keys */
  @Input() settableInfoKeys: Signal<string[]> = signal<string[]>([]);
  newInfo: WritableSignal<InfoEntry> = linkedSignal({
    source: () => this.isEditingInfo(),
    computation: () => {
      return { key: "", value: "" };
    }
  });
  /**
   * The entries as they are edited. It starts from the values of the token and is taken from them again when the
   * editing starts and when they are reloaded, so the shown values stay untouched until a save has been reloaded.
   */
  protected readonly infoDraft: WritableSignal<Record<string, string>> = linkedSignal({
    source: () => ({ editing: this.isEditingInfo(), info: this.asInfoMap(this.infoData()[0]?.value) }),
    computation: ({ info }) => ({ ...info })
  });
  protected readonly infoForm = form(this.infoDraft);
  protected readonly newInfoForm = form(this.newInfo, (path) => {
    infoEntryRules(path, () => Object.keys(this.infoDraft()));
  });
  /** Whether the entries may be saved: the "add" row is empty or complete and names a new key. */
  readonly canSave = computed(() => !this.isEditingInfo() || this.newInfoForm().valid());
  /** The info element for the edit buttons, which disable Save while the "add" row is incomplete. */
  protected readonly editButtonsElement = computed(() => {
    const element = this.infoData()[0] as EditableElement<Record<string, string>> | undefined;
    return element ? { ...element, valid: this.canSave } : undefined;
  });
  protected authService: AuthServiceInterface = inject(AuthService);

  visibleInfoKeys(value: Record<string, string>): string[] {
    return Object.keys(value).filter((k) => !this.hiddenInfoKeys.includes(k));
  }

  asInfoMap(value: unknown): Record<string, string> {
    return (value ?? {}) as Record<string, string>;
  }

  /**
   * Whether the value of an info entry can be changed. Entries the token maintains itself are shown, but read
   * only, unless they have their own endpoint the value can be written through.
   */
  isInfoKeyEditable(key: string): boolean {
    return isTokenInfoKeyWritable(key, this.readonlyInfoKeys(), this.settableInfoKeys());
  }

  /**
   * Whether an info entry can be removed. Removing an entry the token maintains would take away something it
   * needs, except where dropping it only revokes a capability, e.g. an offline refill token.
   */
  isInfoKeyDeletable(key: string): boolean {
    return !this.undeletableInfoKeys().includes(key);
  }

  toggleInfoEdit(): void {
    if (this.isEditingInfo()) {
      this.tokenService.tokenDetailResource.reload();
    }
    this.newInfoForm().reset({ key: "", value: "" });
    this.isEditingInfo.update((b) => !b);
  }

  saveInfo(element: EditableElement<Record<string, string>>): void {
    if (!this.canSave()) {
      this.newInfoForm.key().markAsTouched();
      this.newInfoForm.value().markAsTouched();
      return;
    }
    const entries = { ...this.infoDraft() };
    const { key, value } = this.newInfo();
    if (key.trim() !== "" && value.trim() !== "") {
      entries[key.trim()] = value;
    }
    // Only the entries that were really changed are sent, so that a concurrent change to another entry of the
    // same token is not overwritten with the value this view happened to start with.
    const saved = this.asInfoMap(element.value);
    const changed = Object.fromEntries(
      Object.entries(entries).filter(([entryKey, entryValue]) => entryValue !== saved[entryKey])
    );
    this.tokenService
      .setTokenInfos(this.tokenSerial(), changed, this.readonlyInfoKeys(), this.settableInfoKeys())
      .subscribe({
        next: () => {
          this.newInfoForm().reset({ key: "", value: "" });
          this.tokenService.tokenDetailResource.reload();
        }
      });
    this.isEditingInfo.set(false);
  }

  deleteInfo(key: string): void {
    this.tokenService
      .deleteInfo(this.tokenSerial(), key)
      .pipe(
        switchMap(() => {
          const info = this.detailData().find((detail) => detail.keyMap.key === "info");
          if (info) {
            this.isEditingInfo.set(true);
          }
          return new Observable<void>((observer) => {
            observer.next();
            observer.complete();
          });
        })
      )
      .subscribe({
        next: () => {
          this.tokenService.tokenDetailResource.reload();
        }
      });
  }
}
