import { CommonModule } from '@angular/common';
import { Component, computed } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { Theme, ThemeService } from '../../../services/theme/theme.service';

export type ThemeIcon = 'light_mode' | 'dark_mode' | 'computer';

@Component({
  selector: 'app-theme-switcher',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatMenuModule],
  templateUrl: './theme-switcher.component.html',
  styleUrls: ['./theme-switcher.component.scss'],
})
export class ThemeSwitcherComponent {
  private themeIconMap: Map<Theme, ThemeIcon> = new Map<Theme, ThemeIcon>([
    ['light', 'light_mode'],
    ['dark', 'dark_mode'],
    ['system', 'computer'],
  ]);

  currentThemeIcon = computed<ThemeIcon>(
    () => this.themeIconMap.get(this.themeService.currentTheme())!,
  );

  constructor(private themeService: ThemeService) {}

  setTheme(theme: 'light' | 'dark' | 'system'): void {
    this.themeService.setTheme(theme);
  }
}
