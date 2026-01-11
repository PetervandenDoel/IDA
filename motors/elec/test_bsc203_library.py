"""
BSC203控制器使用示例
演示如何使用bsc203_controller库
"""

from bsc203_controller import BSC203Controller, list_devices, BSC203Exception
import time

def main():
    print("=" * 80)
    print("BSC203 控制器使用示例")
    print("=" * 80)
    
    # 1. 列出所有设备
    print("\n[1] 搜索设备...")
    devices = list_devices()
    if not devices:
        print("❌ 未找到设备")
        return
    
    print(f"✓ 找到 {len(devices)} 个设备:")
    for dev in devices:
        print(f"   {dev}")
    
    try:
        # 2. 创建控制器实例（使用with语句自动连接和断开）
        with BSC203Controller() as controller:
            print("\n[2] 设备已连接")
            
            # 3. 获取设备信息
            info = controller.get_device_info()
            print(f"\n设备信息:")
            print(f"  序列号: {info['serial_number']}")
            print(f"  名称: {info['name']}")
            print(f"  描述: {info['description']}")
            
            # 4. 显示当前位置
            print("\n[3] 当前位置:")
            positions = controller.get_all_positions()
            for axis, pos in positions.items():
                print(f"  {axis}轴: {pos:.3f} mm")
            
            # 5. 设置限位
            print("\n[4] 设置安全限位...")
            controller.set_limits('X', -50, 50)
            controller.set_limits('Y', -50, 50)
            controller.set_limits('Z', -25, 25)
            
            # 6. 获取速度参数
            print("\n[5] 速度参数:")
            for axis in ['X', 'Y', 'Z']:
                vel, acc = controller.get_velocity(axis)
                print(f"  {axis}轴: 速度={vel:.2f} mm/s, 加速度={acc:.2f} mm/s²")
            
            # 询问是否设置零点
            print("\n" + "=" * 80)
            response = input("是否将当前位置设为零点? [y/N]: ").strip().lower()
            
            if response == 'y':
                print("\n[6] 设置零点...")
                for axis in ['X', 'Y', 'Z']:
                    controller.set_zero(axis)
                    print(f"  ✓ {axis}轴已设为零点")
                
                # 显示新位置
                print("\n新位置:")
                positions = controller.get_all_positions()
                for axis, pos in positions.items():
                    print(f"  {axis}轴: {pos:.3f} mm")
            
            # 询问是否移动测试
            print("\n" + "=" * 80)
            response = input("是否进行小距离移动测试? [y/N]: ").strip().lower()
            
            if response == 'y':
                print("\n[7] 移动测试...")
                
                # 测试X轴
                print("\n  测试X轴: 移动 +1mm")
                controller.move_relative('X', 1.0, wait=True)
                pos = controller.get_position('X')
                print(f"  X轴位置: {pos:.3f} mm")
                
                time.sleep(0.5)
                
                print("\n  测试X轴: 返回 -1mm")
                controller.move_relative('X', -1.0, wait=True)
                pos = controller.get_position('X')
                print(f"  X轴位置: {pos:.3f} mm")
                
                print("\n✓ 移动测试完成")
            
            # 演示绝对移动
            print("\n" + "=" * 80)
            response = input("是否测试绝对移动? [y/N]: ").strip().lower()
            
            if response == 'y':
                try:
                    target = input("输入X轴目标位置 (mm): ").strip()
                    target_pos = float(target)
                    
                    print(f"\n移动X轴到 {target_pos} mm...")
                    controller.move_absolute('X', target_pos, wait=True)
                    
                    pos = controller.get_position('X')
                    print(f"✓ X轴已到达: {pos:.3f} mm")
                    
                except ValueError:
                    print("❌ 无效的数值")
                except BSC203Exception as e:
                    print(f"❌ 移动失败: {e}")
            
            print("\n" + "=" * 80)
            print("✓ 测试完成")
        
        print("\n✓ 设备已安全断开")
    
    except BSC203Exception as e:
        print(f"\n❌ 错误: {e}")
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")


if __name__ == "__main__":
    main()
