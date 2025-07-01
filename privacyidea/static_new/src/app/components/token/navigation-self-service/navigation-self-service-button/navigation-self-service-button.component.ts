import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatFabAnchor } from '@angular/material/button';

import { MatIconModule } from '@angular/material/icon';
import { ContentService } from '../../../../services/content/content.service';
import { TokenSelectedContentKey } from '../../token.component';

export type NavigationSelfServiceButtonData = {
  key: TokenSelectedContentKey;
  title: string;
  matIconName?: string;
  matIconClass?: string;
  matIconSize?: 'tile-icon-small' | 'tile-icon-medium' | 'tile-icon-large';
};

@Component({
  selector: 'app-navigation-self-service-button',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatFabAnchor],
  templateUrl: './navigation-self-service-button.component.html',
  styleUrl: './navigation-self-service-button.component.scss',
})
export class NavigationSelfServiceButtonComponent {
  @Input({ required: true }) buttonData!: NavigationSelfServiceButtonData;

  selectedContent = this.contentService.selectedContent;
  constructor(protected readonly contentService: ContentService) {}

  onClick() {
    this.selectedContent.set(this.buttonData.key);
  }
}
