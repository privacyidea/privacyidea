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
import { Component, computed, inject, Signal, WritableSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { PiResponse } from "@app/app.component";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { TokensNotCreatedCalloutComponent } from "@components/container/container-create/tokens-not-created-callout/tokens-not-created-callout.component";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
  ContainerTokenNotCreated
} from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";

export interface ContainerCreationDialogData {
  response: PiResponse<ContainerRegisterData>;
  containerSerial: WritableSignal<string>;
  registerContainer: (containerSerial: string, regenerate: boolean) => void;
  tokensNotCreated?: ContainerTokenNotCreated[];
  /** True when the template created no token at all, so tokensNotCreated is not empty and no token exists. */
  allTokensFailed?: boolean;
}

@Component({
  selector: "app-container-created-dialog",
  imports: [MatButtonModule, MatIcon, DialogWrapperComponent, TokensNotCreatedCalloutComponent],
  templateUrl: "./container-created-dialog.component.html"
})
export class ContainerCreatedDialogComponent extends AbstractDialogComponent<
  Signal<ContainerCreationDialogData | null>
> {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private contentService = inject(ContentService);

  readonly dialogTitle = computed(() =>
    this.data()?.allTokensFailed
      ? $localize`:@@container.containerCreatedWithoutTokens:Container Created Without Tokens`
      : $localize`:@@container.containerSuccessfully:Container Successfully Created`
  );

  constructor() {
    super();
    this.dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }

  navigateContainerDetails(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.navigateContainerDetails(containerSerial);
  }

  regenerateQRCode() {
    const data = this.data();
    if (!data) return;
    data.registerContainer(data.containerSerial(), true);
  }
}
