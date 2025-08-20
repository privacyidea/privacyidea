import { CommonModule } from "@angular/common";
import { Component, computed, inject, Input } from "@angular/core";
import { RouterLink, RouterLinkActive } from "@angular/router";
import { MatFabAnchor } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";

import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";

@Component({
  selector: "app-navigation-self-service-button",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatFabAnchor,
    RouterLink,
    RouterLinkActive
  ],
  templateUrl: "./navigation-self-service-button.component.html",
  styleUrl: "./navigation-self-service-button.component.scss"
})
export class NavigationSelfServiceButtonComponent {
  private readonly contentService: ContentServiceInterface =
    inject(ContentService);
  @Input({ required: true }) key!: string;
  @Input({ required: true }) title!: string;
  @Input() matIconName?: string;
  @Input() matIconClass?: string;
  @Input() matIconSize?:
    | "tile-icon-small"
    | "tile-icon-medium"
    | "tile-icon-large";
  routePath = computed(() => this.key);

  isSelected = computed(() => this.contentService.routeUrl() === this.key);
}
