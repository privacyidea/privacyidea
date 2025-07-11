import { CommonModule } from '@angular/common';
import { Component, computed, Input } from '@angular/core';
import { MatFabAnchor } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ContentService } from '../../../../services/content/content.service';
import { TokenSelectedContentKey } from '../../token.component';

@Component({
  selector: 'app-navigation-self-service-button',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatFabAnchor],
  templateUrl: './navigation-self-service-button.component.html',
  styleUrl: './navigation-self-service-button.component.scss',
})
export class NavigationSelfServiceButtonComponent {
  @Input({ required: true }) key!: TokenSelectedContentKey;
  @Input({ required: true }) title!: string;
  @Input() matIconName?: string;
  @Input() matIconClass?: string;
  @Input() matIconSize?:
    | 'tile-icon-small'
    | 'tile-icon-medium'
    | 'tile-icon-large';

  selectedContent = this.contentService.selectedContent;
  isSelected = computed(() => {
    return this.selectedContent() === this.key;
  });

  constructor(protected readonly contentService: ContentService) {}

  onClick() {
    this.selectedContent.set(this.key);
  }
}
