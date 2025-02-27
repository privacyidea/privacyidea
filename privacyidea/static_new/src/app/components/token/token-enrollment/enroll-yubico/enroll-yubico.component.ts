import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { SystemService } from '../../../../services/system/system.service';

@Component({
  selector: 'app-enroll-yubico',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-yubico.component.html',
  styleUrl: './enroll-yubico.component.scss',
})
export class EnrollYubicoComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'yubico')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() yubikeyIdentifier!: WritableSignal<string>;
  yubicoIsConfigured = signal(false);

  constructor(private systemService: SystemService) {}

  ngOnInit(): void {
    this.systemService.getSystemConfig().subscribe((response) => {
      const config = response?.result?.value;
      if (
        config &&
        config['yubico.id'] &&
        config['yubico.url'] &&
        config['yubico.secret']
      ) {
        this.yubicoIsConfigured.set(true);
      }
    });
  }
}
