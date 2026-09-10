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
import { Component, inject, Input, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { EditableElement, EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  isTokenInfoKeyWritable,
  TokenService,
  TokenServiceInterface
} from "@services/token/token.service";
import { Observable, switchMap } from "rxjs";
import { TIMESTAMP_INFO_KEYS } from "../token-details.constants";

@Component({
  selector: "app-token-details-info",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    FormsModule,
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
  protected readonly hiddenInfoKeys: readonly string[] = TIMESTAMP_INFO_KEYS;
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
  newInfo: WritableSignal<{ key: string; value: string }> = linkedSignal({
    source: () => this.isEditingInfo(),
    computation: () => {
      return { key: "", value: "" };
    }
  });
  /**
   * The values as they were when the editing started, so that saving only sends the entries that were really
   * changed. Sending all of them would overwrite what somebody else changed in the meantime.
   *
   * This is filled when the editing starts, not when it is read: the inputs are bound to the value map of the
   * element itself, so by the time it is saved that map already holds the edited values.
   */
  editedInfoBefore: WritableSignal<Record<string, string>> = signal<Record<string, string>>({});
  protected authService: AuthServiceInterface = inject(AuthService);

  visibleInfoKeys(value: Record<string, string>): string[] {
    return Object.keys(value).filter((k) => !this.hiddenInfoKeys.includes(k));
  }

  asInfoMap(value: unknown): Record<string, string> {
    return (value ?? {}) as Record<string, string>;
  }

  asInfoElement(element: EditableElement): EditableElement<Record<string, string>> {
    return element as EditableElement<Record<string, string>>;
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
    } else {
      this.editedInfoBefore.set({ ...this.asInfoMap(this.infoData()[0]?.value) });
    }
    this.isEditingInfo.update((b) => !b);
  }

  saveInfo(element: EditableElement<Record<string, string>>): void {
    if (this.newInfo().key.trim() !== "" && this.newInfo().value.trim() !== "") {
      element.value[this.newInfo().key] = this.newInfo().value;
    }
    // Only the entries that were really changed are sent, so that a concurrent change to another entry of the
    // same token is not overwritten with the value this view happened to start with. Without a record of what
    // the editing started from, everything is sent, which is what happened before it was recorded.
    const before = this.editedInfoBefore();
    let changed = element.value;
    if (Object.keys(before).length) {
      changed = Object.fromEntries(
        Object.keys(element.value)
          .filter((key) => element.value[key] !== before[key])
          .map((key) => [key, element.value[key]])
      );
    }
    this.tokenService
      .setTokenInfos(this.tokenSerial(), changed, this.readonlyInfoKeys(), this.settableInfoKeys())
      .subscribe({
        next: () => {
          this.newInfo.set({ key: "", value: "" });
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
