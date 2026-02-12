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
import { Component, computed, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatDividerModule } from "@angular/material/divider";
import { MatCardModule } from "@angular/material/card";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { SubscriptionService } from "../../../services/subscription/subscription.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { AuthService } from "../../../services/auth/auth.service";

@Component({
  selector: "app-subscription",
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatExpansionModule,
    MatIconModule,
    MatDividerModule,
    MatCardModule,
    MatTooltipModule,
    ScrollToTopDirective
  ],
  templateUrl: "./subscription.component.html",
  styleUrl: "./subscription.component.scss"
})
export class SubscriptionComponent {
  private subscriptionService = inject(SubscriptionService);
  private notificationService = inject(NotificationService);
  subscriptionsResource = this.subscriptionService.subscriptionsResource;
  subscriptions = computed(() => {
    const value = this.subscriptionsResource.value()?.result?.value;
    return value ? Object.values(value) : [];
  });
  protected authService = inject(AuthService);

  upload(event: Event): void {
    const element = event.currentTarget as HTMLInputElement;
    let fileList: FileList | null = element.files;
    if (fileList && fileList.length > 0) {
      this.subscriptionService.uploadSubscriptionFile(fileList[0]).subscribe(() => {
        this.notificationService.openSnackBar("File uploaded successfully.");
        this.subscriptionService.reload();
      });
    }
  }

  deleteSubscription(application: string): void {
    this.subscriptionService.deleteSubscription(application).subscribe(() => {
      this.notificationService.openSnackBar("Subscription deleted successfully.");
      this.subscriptionService.reload();
    });
  }
}
