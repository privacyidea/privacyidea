import { Component, computed, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { ROUTE_PATHS } from "../../../../../route_paths";

@Component({
  selector: 'app-sms-config',
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
  templateUrl: './sms-config.component.html',
  styles: `
    :host {
      display: block;
    }
  `
})
export class SmsConfigComponent {
  formData = input.required<Record<string, any>>();
  smsGateways = input.required<string[]>();
  providerName = computed(() => {
    const provider = this.formData()['sms.Provider'];
    return provider ? provider.split('.').pop() : '';
  });
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
