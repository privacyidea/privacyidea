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

import { TitleCasePipe } from "@angular/common";
import { Component, computed, inject, signal } from "@angular/core";
import { MatProgressBar } from "@angular/material/progress-bar";
import { EnrollmentResponseDetail } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogAction } from "@models/dialog";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";

export type EnrolledTokenInfo = EnrollmentResponseDetail & { type: string; serial: string };

export type ContainerTokensEnrolledDialogData = {
  enrolledTokens: EnrolledTokenInfo[];
  containerSerial: string;
};

@Component({
  selector: "app-container-tokens-enrolled-dialog",
  imports: [MatProgressBar, TokenEnrollmentDataComponent, TitleCasePipe, DialogWrapperComponent],
  templateUrl: "./container-tokens-enrolled-dialog.component.html",
  styleUrl: "./container-tokens-enrolled-dialog.component.scss"
})
export class ContainerTokensEnrolledDialogComponent extends AbstractDialogComponent<ContainerTokensEnrolledDialogData> {
  private readonly contentService: ContentServiceInterface = inject(ContentService);

  readonly currentIndex = signal(0);

  readonly currentToken = computed(() => this.data.enrolledTokens[this.currentIndex()]);
  readonly total = computed(() => this.data.enrolledTokens.length);
  readonly progress = computed(() => ((this.currentIndex() + 1) / this.total()) * 100);
  readonly isFirst = computed(() => this.currentIndex() === 0);
  readonly isLast = computed(() => this.currentIndex() === this.total() - 1);

  readonly dialogActions = computed((): DialogAction<string>[] => [
    {
      type: "auxiliary",
      label: $localize`Previous`,
      value: "previous",
      icon: "arrow_back",
      disabled: this.isFirst()
    },
    this.isLast()
      ? { type: "confirm", label: $localize`Go to Container`, value: "finish", primary: true, icon: "check" }
      : { type: "auxiliary", label: $localize`Next`, value: "next", primary: true, icon: "arrow_forward" }
  ]);

  onDialogAction(value: string) {
    if (value === "previous") this.previous();
    else if (value === "next") this.next();
    else if (value === "finish") this.finish();
  }

  next() {
    if (!this.isLast()) this.currentIndex.update((i) => i + 1);
  }

  previous() {
    if (!this.isFirst()) this.currentIndex.update((i) => i - 1);
  }

  finish() {
    this.dialogRef.close();
    this.contentService.navigateContainerDetails(this.data.containerSerial);
  }
}
