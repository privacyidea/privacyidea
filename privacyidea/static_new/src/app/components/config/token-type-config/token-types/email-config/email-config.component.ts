import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { ROUTE_PATHS } from "../../../../../route_paths";

@Component({
  selector: 'app-email-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    RouterLink
  ],
  templateUrl: './email-config.component.html',
  styles: `
    :host {
      display: block;
    }
  `
})
export class EmailConfigComponent {
  formData = input.required<Record<string, any>>();
  smtpServers = input.required<string[]>();
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
