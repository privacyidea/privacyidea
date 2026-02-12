import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { ROUTE_PATHS } from "../../../../../route_paths";

@Component({
  selector: 'app-radius-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatSelectModule,
    RouterLink
  ],
  templateUrl: './radius-config.component.html',
  styles: `
    :host {
      display: block;
    }
  `
})
export class RadiusConfigComponent {
  formData = input.required<Record<string, any>>();
  radiusServers = input.required<string[]>();
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
